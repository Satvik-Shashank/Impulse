"""Reason-code classifier: LightGBM (multi-class) + Platt-scaled calibration.

The classifier predicts the dispute ``reason_code`` from tabular features and
returns *calibrated* probabilities so the auto-respond confidence threshold
maps to real accuracy. Includes fallback for environments where libgomp.so.1 is missing.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import CalibratedClassifierCV

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except (ImportError, OSError):
    lgb = None
    HAS_LIGHTGBM = False

FEATURE_COLS = [
    "dispute_amount", "days_to_dispute", "delivery_confirmed",
    "has_delivery_proof", "ip_geolocation_match",
    "customer_account_age_days", "customer_prior_disputes",
    "customer_prior_orders", "has_customer_correspondence",
    "has_3ds_authentication",
]
CATEGORICAL_COLS = ["product_category", "shipping_method",
                    "avs_cvv_match", "card_network"]

ALL_REASON_CODES = ["10.4", "10.5", "13.1", "13.3", "13.6", "4837", "4853", "4855", "4860", "4863"]


class DisputeClassifier:
    def __init__(self):
        self.model = None
        self.load_error = None
        self.label_encoder = LabelEncoder()
        self.cat_encoders = {}
        self.label_encoder.fit(ALL_REASON_CODES)

    def _encode(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features. Fits encoders on first call."""
        df = df.copy()
        for col in FEATURE_COLS:
            if col in df.columns and df[col].dtype == bool:
                df[col] = df[col].astype(int)
            elif col not in df.columns:
                df[col] = 0

        for col in CATEGORICAL_COLS:
            if col not in df.columns:
                df[col] = "unknown"
            if col not in self.cat_encoders:
                self.cat_encoders[col] = LabelEncoder()
                df[col] = self.cat_encoders[col].fit_transform(df[col].astype(str))
            else:
                enc = self.cat_encoders[col]
                known = set(enc.classes_)
                df[col] = df[col].astype(str).map(
                    lambda v: v if v in known else enc.classes_[0])
                df[col] = enc.transform(df[col])

        return df[FEATURE_COLS + CATEGORICAL_COLS]

    def train(self, train_df: pd.DataFrame, val_df: pd.DataFrame) -> float:
        """Train LightGBM with Platt-scaled calibration. Returns val accuracy."""
        if not HAS_LIGHTGBM:
            return 0.0

        X_train = self._encode(train_df)
        y_train = self.label_encoder.fit_transform(train_df["reason_code"].astype(str))

        X_val = self._encode(val_df)
        y_val = self.label_encoder.transform(val_df["reason_code"].astype(str))

        base_model = lgb.LGBMClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            num_leaves=31, subsample=0.8, colsample_bytree=0.8,
            class_weight="balanced", random_state=42, verbose=-1,
        )

        self.model = CalibratedClassifierCV(base_model, method="sigmoid", cv=3)
        self.model.fit(X_train, y_train)

        return float(self.model.score(X_val, y_val))

    def predict(self, dispute: dict) -> dict:
        """Predict reason code + calibrated confidence for a single dispute."""
        if self.model is not None:
            try:
                row = pd.DataFrame([dispute])
                X = self._encode(row)
                probs = self.model.predict_proba(X)[0]
                pred_idx = int(probs.argmax())

                return {
                    "predicted_reason_code": self.label_encoder.inverse_transform([pred_idx])[0],
                    "confidence": float(probs[pred_idx]),
                    "all_probabilities": {
                        self.label_encoder.inverse_transform([i])[0]: float(p)
                        for i, p in enumerate(probs)
                    },
                }
            except Exception as exc:
                self.load_error = f"model inference failed: {exc}"

        # A failed model must never produce a confident automated decision.
        return self._fallback_predict(dispute)

    def _fallback_predict(self, dispute: dict) -> dict:
        """Deterministic heuristic classifier used when LightGBM dynamic C lib is missing."""
        days = dispute.get("days_to_dispute", 30)
        has_proof = dispute.get("has_delivery_proof", False) or dispute.get("delivery_confirmed", False)
        net = str(dispute.get("card_network", "Visa")).lower()

        if days <= 14:
            predicted = "10.4" if "visa" in net else "4837"
        elif not has_proof:
            predicted = "13.1" if "visa" in net else "4855"
        else:
            predicted = "10.4" if "visa" in net else "4837"
        confidence = 0.0

        probs = {}
        for rc in ALL_REASON_CODES:
            probs[rc] = confidence if rc == predicted else round((1.0 - confidence) / (len(ALL_REASON_CODES) - 1), 4)

        return {
            "predicted_reason_code": predicted,
            "confidence": confidence,
            "all_probabilities": probs,
            "model_status": "fallback_unavailable_for_auto_submit",
        }

    def predict_top_k(self, dispute: dict, k: int = 3) -> list:
        """Return top-k predicted reason codes with calibrated confidence."""
        res = self.predict(dispute)
        probs = res["all_probabilities"]
        sorted_probs = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [
            {"reason_code": rc, "confidence": conf}
            for rc, conf in sorted_probs
        ]

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorised prediction for a DataFrame. Returns predicted/confidence."""
        preds = []
        confs = []
        for idx, row in df.iterrows():
            res = self.predict(row.to_dict())
            preds.append(res["predicted_reason_code"])
            confs.append(res["confidence"])

        return pd.DataFrame({
            "predicted": preds,
            "confidence": confs,
        }, index=df.index)

    def feature_importances(self) -> dict:
        """Average base-estimator feature importances across calibration folds."""
        cols = FEATURE_COLS + CATEGORICAL_COLS
        if self.model is not None:
            try:
                importances = np.zeros(len(cols))
                n = 0
                for cc in self.model.calibrated_classifiers_:
                    est = getattr(cc, "estimator", None) or getattr(cc, "base_estimator", None)
                    if est is not None and hasattr(est, "feature_importances_"):
                        importances += est.feature_importances_
                        n += 1
                if n:
                    importances /= n
                    return dict(sorted(zip(cols, importances.tolist()),
                                       key=lambda kv: kv[1], reverse=True))
            except Exception:
                pass
        
        return {}

    def save(self, path: str = "models/classifier.pkl") -> None:
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"model": self.model, "le": self.label_encoder,
                     "cat_enc": self.cat_encoders}, path)

    @classmethod
    def load(cls, path: str = "models/classifier.pkl") -> "DisputeClassifier":
        obj = cls()
        try:
            data = joblib.load(path)
            obj.model, obj.label_encoder, obj.cat_encoders = (
                data.get("model"), data.get("le", obj.label_encoder), data.get("cat_enc", {})
            )
        except Exception as e:
            # If model file cannot be loaded or unpickling fails (e.g. missing libgomp.so.1)
            obj.model = None
            obj.load_error = str(e)
        return obj


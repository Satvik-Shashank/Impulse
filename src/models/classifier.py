"""Reason-code classifier: LightGBM (multi-class) + Platt-scaled calibration.

The classifier predicts the dispute ``reason_code`` from tabular features and
returns *calibrated* probabilities so the auto-respond confidence threshold
maps to real accuracy.
"""

import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import CalibratedClassifierCV

FEATURE_COLS = [
    "dispute_amount", "days_to_dispute", "delivery_confirmed",
    "has_delivery_proof", "ip_geolocation_match",
    "customer_account_age_days", "customer_prior_disputes",
    "customer_prior_orders", "has_customer_correspondence",
    "has_3ds_authentication",
]
CATEGORICAL_COLS = ["product_category", "shipping_method",
                    "avs_cvv_match", "card_network"]


class DisputeClassifier:
    def __init__(self):
        self.model = None
        self.label_encoder = LabelEncoder()
        self.cat_encoders = {}

    def _encode(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features. Fits encoders on first call."""
        df = df.copy()
        for col in FEATURE_COLS:
            if df[col].dtype == bool:
                df[col] = df[col].astype(int)

        for col in CATEGORICAL_COLS:
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

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorised prediction for a DataFrame. Returns predicted/confidence."""
        X = self._encode(df)
        probs = self.model.predict_proba(X)
        pred_idx = probs.argmax(axis=1)
        preds = self.label_encoder.inverse_transform(pred_idx)
        confidence = probs[np.arange(len(probs)), pred_idx]

        return pd.DataFrame({
            "predicted": preds,
            "confidence": confidence,
        }, index=df.index)

    def feature_importances(self) -> dict:
        """Average base-estimator feature importances across calibration folds."""
        cols = FEATURE_COLS + CATEGORICAL_COLS
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

    def save(self, path: str = "models/classifier.pkl") -> None:
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"model": self.model, "le": self.label_encoder,
                     "cat_enc": self.cat_encoders}, path)

    @classmethod
    def load(cls, path: str = "models/classifier.pkl") -> "DisputeClassifier":
        obj = cls()
        data = joblib.load(path)
        obj.model, obj.label_encoder, obj.cat_encoders = (
            data["model"], data["le"], data["cat_enc"])
        return obj

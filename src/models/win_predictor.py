"""Win-probability predictor: LightGBM (binary) + Platt-scaled calibration.

Predicts the probability that a merchant will WIN a chargeback dispute,
given the evidence available and dispute characteristics. This is a separate
model from the reason-code classifier, trained on the `outcome` column
(merchant_won vs merchant_lost).

The calibrated probability is used in the cost-sensitive decision engine to
compute the expected value of auto-responding vs. routing to human review.
"""

import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV


WIN_FEATURE_COLS = [
    "dispute_amount", "days_to_dispute", "delivery_confirmed",
    "has_delivery_proof", "ip_geolocation_match",
    "customer_account_age_days", "customer_prior_disputes",
    "customer_prior_orders", "has_customer_correspondence",
    "has_3ds_authentication",
]


class WinPredictor:
    """Calibrated binary classifier predicting merchant win probability."""

    def __init__(self):
        self.model = None

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract and encode features for the win predictor."""
        df = df.copy()
        for col in WIN_FEATURE_COLS:
            if col in df.columns and df[col].dtype == bool:
                df[col] = df[col].astype(int)
        available_cols = [c for c in WIN_FEATURE_COLS if c in df.columns]
        result = df[available_cols].copy()
        # Fill any missing columns with 0
        for col in WIN_FEATURE_COLS:
            if col not in result.columns:
                result[col] = 0
        return result[WIN_FEATURE_COLS]

    def train(self, train_df: pd.DataFrame, val_df: pd.DataFrame) -> float:
        """Train a calibrated LightGBM binary classifier. Returns val AUC."""
        X_train = self._prepare_features(train_df)
        y_train = (train_df["outcome"] == "merchant_won").astype(int).values

        X_val = self._prepare_features(val_df)
        y_val = (val_df["outcome"] == "merchant_won").astype(int).values

        base_model = lgb.LGBMClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=5,
            num_leaves=31, subsample=0.8, colsample_bytree=0.8,
            class_weight="balanced", random_state=42, verbose=-1,
        )

        self.model = CalibratedClassifierCV(base_model, method="sigmoid", cv=3)
        self.model.fit(X_train, y_train)

        from sklearn.metrics import roc_auc_score
        probs = self.model.predict_proba(X_val)[:, 1]
        try:
            auc = float(roc_auc_score(y_val, probs))
        except ValueError:
            auc = float("nan")
        return auc

    def predict_win_probability(self, dispute: dict) -> float:
        """Return calibrated P(merchant_won) for a single dispute."""
        row = pd.DataFrame([dispute])
        X = self._prepare_features(row)
        probs = self.model.predict_proba(X)[0]
        # Index 1 = merchant_won
        return float(probs[1])

    def predict_batch(self, df: pd.DataFrame) -> np.ndarray:
        """Return array of P(merchant_won) for a DataFrame."""
        X = self._prepare_features(df)
        return self.model.predict_proba(X)[:, 1]

    def feature_importances(self) -> dict:
        """Average feature importances across calibration folds."""
        importances = np.zeros(len(WIN_FEATURE_COLS))
        n = 0
        for cc in self.model.calibrated_classifiers_:
            est = getattr(cc, "estimator", None) or getattr(cc, "base_estimator", None)
            if est is not None and hasattr(est, "feature_importances_"):
                importances += est.feature_importances_
                n += 1
        if n:
            importances /= n
        return dict(sorted(zip(WIN_FEATURE_COLS, importances.tolist()),
                           key=lambda kv: kv[1], reverse=True))

    def save(self, path: str = "models/win_predictor.pkl") -> None:
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"model": self.model}, path)

    @classmethod
    def load(cls, path: str = "models/win_predictor.pkl") -> "WinPredictor":
        obj = cls()
        data = joblib.load(path)
        obj.model = data["model"]
        return obj

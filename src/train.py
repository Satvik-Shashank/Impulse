"""Train the reason-code classifier and persist it to models/classifier.pkl.

Usage:
    python -m src.train
"""

import pandas as pd
from src.models.classifier import DisputeClassifier


def main(train_path="data/disputes_train.csv",
         val_path="data/disputes_val.csv",
         model_path="models/classifier.pkl"):
    train_df = pd.read_csv(train_path, dtype={"reason_code": str})
    val_df = pd.read_csv(val_path, dtype={"reason_code": str})

    clf = DisputeClassifier()
    val_acc = clf.train(train_df, val_df)
    clf.save(model_path)

    print(f"Validation accuracy: {val_acc:.4f}")
    print(f"Model saved to: {model_path}")
    print("\nTop feature importances:")
    for feat, imp in list(clf.feature_importances().items())[:10]:
        print(f"  {feat:32s} {imp:.1f}")


if __name__ == "__main__":
    main()

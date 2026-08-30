"""Tests for the reason-code classifier."""

from src.data.generate_disputes import build_dataset
from src.models.classifier import DisputeClassifier


def test_predict_output_shape(trained_model):
    clf = DisputeClassifier.load(trained_model)
    dispute = build_dataset(n=1).iloc[0].to_dict()
    out = clf.predict(dispute)
    assert "predicted_reason_code" in out
    assert 0.0 <= out["confidence"] <= 1.0
    assert abs(sum(out["all_probabilities"].values()) - 1.0) < 1e-6


def test_batch_matches_single(trained_model):
    clf = DisputeClassifier.load(trained_model)
    df = build_dataset(n=20)
    batch = clf.predict_batch(df)
    assert len(batch) == 20
    single = clf.predict(df.iloc[0].to_dict())
    assert batch.iloc[0]["predicted"] == single["predicted_reason_code"]


def test_feature_importances_nonempty(trained_model):
    clf = DisputeClassifier.load(trained_model)
    fi = clf.feature_importances()
    assert len(fi) > 0


def test_classifier_beats_random_baseline(trained_model, small_dataset):
    """The classifier must do meaningfully better than guessing — this is
    the regression test that guards against reason_code being independent
    of the features again in the future."""
    _, val = small_dataset
    clf = DisputeClassifier.load(trained_model)
    batch = clf.predict_batch(val)
    accuracy = (batch["predicted"].values == val["reason_code"].astype(str).values).mean()
    n_classes = val["reason_code"].nunique()
    random_baseline = 1.0 / n_classes
    assert accuracy > random_baseline * 1.5, (
        f"Accuracy ({accuracy:.3f}) is too close to random baseline "
        f"({random_baseline:.3f}) — check that reason_code correlates with features."
    )

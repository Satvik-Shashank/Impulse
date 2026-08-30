"""Shared pytest fixtures: a small trained classifier for pipeline tests."""

import pytest
from src.data.generate_disputes import build_dataset
from src.models.classifier import DisputeClassifier


@pytest.fixture(scope="session")
def small_dataset():
    df = build_dataset(n=800)
    n = len(df)
    train = df.iloc[: int(n * 0.7)]
    val = df.iloc[int(n * 0.7):]
    return train, val


@pytest.fixture(scope="session")
def trained_model(small_dataset, tmp_path_factory):
    train, val = small_dataset
    clf = DisputeClassifier()
    clf.train(train, val)
    path = tmp_path_factory.mktemp("models") / "classifier.pkl"
    clf.save(str(path))
    return str(path)

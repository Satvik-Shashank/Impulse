"""Tests for the win probability predictor."""

import pytest
import os
import pandas as pd
from src.data.generate_disputes import build_dataset
from src.models.win_predictor import WinPredictor


@pytest.fixture
def win_model(tmp_path):
    train_df = build_dataset(n=100)
    val_df = build_dataset(n=30)
    wp = WinPredictor()
    wp.train(train_df, val_df)
    model_file = os.path.join(tmp_path, "win_predictor.pkl")
    wp.save(model_file)
    return model_file


def test_predict_win_probability_range(win_model):
    wp = WinPredictor.load(win_model)
    dispute = build_dataset(n=1).iloc[0].to_dict()
    prob = wp.predict_win_probability(dispute)
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


def test_predict_batch_win_probability(win_model):
    wp = WinPredictor.load(win_model)
    df = build_dataset(n=10)
    probs = wp.predict_batch(df)
    assert len(probs) == 10
    assert all(0.0 <= p <= 1.0 for p in probs)


def test_win_predictor_feature_importances(win_model):
    wp = WinPredictor.load(win_model)
    fi = wp.feature_importances()
    assert len(fi) > 0
    assert "evidence_strength" in fi or "delivery_confirmed" in fi

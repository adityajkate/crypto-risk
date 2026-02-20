import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from training.train_risk_classifier import RiskClassifierTrainer

@pytest.fixture
def labeled_features(tmp_path):
    """Create labeled feature data."""
    processed_dir = tmp_path / "processed"
    artifacts_dir = tmp_path / "artifacts"
    processed_dir.mkdir()
    artifacts_dir.mkdir()

    np.random.seed(42)
    n_samples = 300

    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n_samples, freq="D"),
        "coin_id": ["bitcoin"] * n_samples,
        "returns_1d": np.random.randn(n_samples),
        "log_returns": np.random.randn(n_samples) * 0.02,
        "volatility_7d": np.random.uniform(0.01, 0.05, n_samples),
        "volatility_30d": np.random.uniform(0.01, 0.1, n_samples),
        "rsi_14": np.random.uniform(0, 100, n_samples),
        "macd": np.random.randn(n_samples),
        "macd_signal": np.random.randn(n_samples),
        "macd_hist": np.random.randn(n_samples),
        "bb_upper": np.random.uniform(100, 200, n_samples),
        "bb_lower": np.random.uniform(50, 100, n_samples),
        "bb_width": np.random.uniform(0.1, 0.5, n_samples),
        "atr_14": np.random.uniform(1, 10, n_samples),
        "obv": np.random.uniform(1000, 10000, n_samples),
        "volume_sma_ratio": np.random.uniform(0.5, 3, n_samples),
        "drawdown": np.random.uniform(-50, 0, n_samples),
        "price_sma50_ratio": np.random.uniform(0.8, 1.2, n_samples),
        "price_sma200_ratio": np.random.uniform(0.8, 1.2, n_samples),
        "risk_label": np.random.choice([0, 1, 2], n_samples)
    })

    df.to_csv(processed_dir / "features_with_labels.csv", index=False)
    return processed_dir, artifacts_dir

def test_trainer_initialization(labeled_features):
    processed_dir, artifacts_dir = labeled_features
    trainer = RiskClassifierTrainer(processed_dir=processed_dir, artifacts_dir=artifacts_dir)
    assert trainer.processed_dir == processed_dir
    assert trainer.artifacts_dir == artifacts_dir

def test_trainer_creates_artifacts(labeled_features):
    processed_dir, artifacts_dir = labeled_features
    trainer = RiskClassifierTrainer(processed_dir=processed_dir, artifacts_dir=artifacts_dir)
    trainer.run()

    assert (artifacts_dir / "risk_logreg.joblib").exists()
    assert (artifacts_dir / "risk_rf.joblib").exists()
    assert (artifacts_dir / "risk_xgb.joblib").exists()
    assert (artifacts_dir / "risk_best.joblib").exists()
    assert (artifacts_dir / "scaler.joblib").exists()

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from training.label_generator import LabelGenerator

@pytest.fixture
def sample_features(tmp_path):
    """Create sample feature data."""
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()

    np.random.seed(42)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=500, freq="D"),
        "coin_id": ["bitcoin"] * 250 + ["ethereum"] * 250,
        "volatility_30d": np.random.uniform(0.01, 0.1, 500),
        "drawdown": np.random.uniform(-50, 0, 500),
        "volume_sma_ratio": np.random.uniform(0.5, 3, 500)
    })

    df.to_csv(processed_dir / "features.csv", index=False)
    return processed_dir

def test_label_generator_initialization(sample_features):
    gen = LabelGenerator(processed_dir=sample_features)
    assert gen.processed_dir == sample_features

def test_generate_labels_creates_output(sample_features):
    gen = LabelGenerator(processed_dir=sample_features)
    gen.run()

    output_file = sample_features / "features_with_labels.csv"
    assert output_file.exists()

    df = pd.read_csv(output_file)
    assert "risk_label" in df.columns
    assert df["risk_label"].isin([0, 1, 2]).all()
    assert len(df[df["risk_label"] == 0]) > 0
    assert len(df[df["risk_label"] == 1]) > 0
    assert len(df[df["risk_label"] == 2]) > 0

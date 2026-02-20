import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from training.preprocess import Preprocessor

@pytest.fixture
def mock_raw_data(tmp_path):
    """Create mock raw data files."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)

    dates = pd.date_range("2024-01-01", periods=250, freq="D")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(250) * 2)

    for coin in ["bitcoin", "ethereum"]:
        df = pd.DataFrame({
            "timestamp": dates,
            "price": prices,
            "volume": np.random.randint(100000, 1000000, 250),
            "market_cap": prices * 100000
        })
        df.to_csv(raw_dir / f"{coin}_history.csv", index=False)

    return raw_dir

def test_preprocessor_initialization(mock_raw_data, tmp_path):
    processed_dir = tmp_path / "processed"
    prep = Preprocessor(raw_dir=mock_raw_data, processed_dir=processed_dir)
    assert prep.raw_dir == mock_raw_data
    assert prep.processed_dir == processed_dir

def test_preprocess_creates_output(mock_raw_data, tmp_path):
    processed_dir = tmp_path / "processed"
    prep = Preprocessor(raw_dir=mock_raw_data, processed_dir=processed_dir)
    prep.run()

    output_file = processed_dir / "features.csv"
    assert output_file.exists()

    df = pd.read_csv(output_file)
    assert "coin_id" in df.columns
    assert len(df) > 0

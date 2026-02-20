import pytest
import pandas as pd
from pathlib import Path
from training.collect_training_data import TrainingDataCollector

@pytest.fixture
def temp_data_dir(tmp_path):
    return tmp_path / "data" / "raw"

def test_collector_initialization(temp_data_dir):
    collector = TrainingDataCollector(output_dir=temp_data_dir, coin_limit=5)
    assert collector.coin_limit == 5
    assert collector.output_dir == temp_data_dir

def test_save_raw_data(temp_data_dir):
    collector = TrainingDataCollector(output_dir=temp_data_dir, coin_limit=5)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=3),
        "price": [100.0, 101.0, 102.0],
        "volume": [1000, 1100, 1200],
        "market_cap": [1000000, 1100000, 1200000]
    })
    collector._save_raw_data("testcoin", df)

    saved_file = temp_data_dir / "testcoin_history.csv"
    assert saved_file.exists()

    loaded = pd.read_csv(saved_file)
    assert len(loaded) == 3

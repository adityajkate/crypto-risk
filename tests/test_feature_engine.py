import pytest
import pandas as pd
import numpy as np
from shared.feature_engine import MarketFeatureEngine

@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV data."""
    dates = pd.date_range("2024-01-01", periods=250, freq="D")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(250) * 2)

    return pd.DataFrame({
        "timestamp": dates,
        "open": prices * 0.99,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(100000, 1000000, 250)
    })

def test_feature_engine_initialization():
    engine = MarketFeatureEngine()
    assert engine is not None

def test_transform_returns_expected_features(sample_ohlcv):
    engine = MarketFeatureEngine()
    result = engine.transform(sample_ohlcv)

    expected_features = [
        "returns_1d", "log_returns", "volatility_7d", "volatility_30d",
        "rsi_14", "macd", "macd_signal", "macd_hist",
        "bb_upper", "bb_lower", "bb_width",
        "atr_14", "obv", "volume_sma_ratio",
        "drawdown", "price_sma50_ratio", "price_sma200_ratio"
    ]

    for feature in expected_features:
        assert feature in result.columns, f"Missing feature: {feature}"

def test_transform_drops_nan_rows(sample_ohlcv):
    engine = MarketFeatureEngine()
    result = engine.transform(sample_ohlcv)
    assert result.isna().sum().sum() == 0, "Result should have no NaN values"

def test_rsi_range(sample_ohlcv):
    engine = MarketFeatureEngine()
    result = engine.transform(sample_ohlcv)
    rsi = result["rsi_14"].dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all(), "RSI should be in [0, 100]"

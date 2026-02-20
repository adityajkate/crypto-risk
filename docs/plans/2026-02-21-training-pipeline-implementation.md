# Crypto Risk Lens Training Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the complete training pipeline for Crypto Risk Lens: data collection from CoinGecko, feature engineering, label generation, and model training for risk classification, volatility regression, clustering, and regime detection.

**Architecture:** Modular Python scripts with a shared feature engine. Each script is standalone and runnable independently. All artifacts saved as `.joblib` files. No database - filesystem-only persistence.

**Tech Stack:** Python 3.11+, Pandas, NumPy, scikit-learn, XGBoost, TA-Lib, hmmlearn, ruptures, statsmodels, httpx

---

## Prerequisites

### Task 0: Setup Project Structure

**Files:**
- Create: `requirements-train.txt`
- Create: `shared/__init__.py`
- Create: `training/__init__.py`
- Create: `training/data/raw/.gitkeep`
- Create: `training/data/processed/.gitkeep`
- Create: `artifacts/.gitignore`

**Step 1: Create requirements file**

```txt
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
ta-lib>=0.4.0
joblib>=1.3.0
hmmlearn>=0.3.0
ruptures>=1.1.0
statsmodels>=0.14.0
httpx>=0.25.0
python-dotenv>=1.0.0
vaderSentiment>=3.3.2
```

**Step 2: Create directory structure**

```bash
mkdir -p shared training/data/raw training/data/processed artifacts
```

**Step 3: Create __init__.py files**

```python
# shared/__init__.py
"""Shared utilities for training and inference."""
```

```python
# training/__init__.py
"""Training pipeline scripts."""
```

**Step 4: Create .gitignore for artifacts**

```
# artifacts/.gitignore
*
!.gitignore
```

**Step 5: Commit**

```bash
git add .
git commit -m "chore: setup training pipeline structure"
```

---

## Phase 1: Data Collection

### Task 1: CoinGecko Client

**Files:**
- Create: `shared/coingecko_client.py`
- Create: `tests/test_coingecko_client.py`

**Step 1: Write failing test**

```python
import pytest
import httpx
from shared.coingecko_client import CoinGeckoClient

@pytest.mark.asyncio
async def test_fetch_top_coins():
    client = CoinGeckoClient()
    coins = await client.fetch_top_coins(limit=5)
    assert len(coins) == 5
    assert all('id' in c for c in coins)
    assert all('symbol' in c for c in coins)
    await client.close()

@pytest.mark.asyncio
async def test_fetch_coin_history():
    client = CoinGeckoClient()
    df = await client.fetch_coin_history('bitcoin', days=30)
    assert not df.empty
    assert 'timestamp' in df.columns
    assert 'price' in df.columns
    assert 'volume' in df.columns
    await client.close()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_coingecko_client.py -v
```
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
import asyncio
import httpx
import pandas as pd
from typing import List, Dict, Any

class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"
    RATE_LIMIT_DELAY = 1.5  # 40 req/min max

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._last_request_time = 0

    async def _rate_limited_request(self, endpoint: str, params: dict = None) -> dict:
        """Make rate-limited request to CoinGecko API."""
        import time
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)

        url = f"{self.BASE_URL}/{endpoint}"
        response = await self.client.get(url, params=params)
        self._last_request_time = time.time()

        response.raise_for_status()
        return response.json()

    async def fetch_top_coins(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch top coins by market cap."""
        data = await self._rate_limited_request(
            "coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1
            }
        )
        return [{"id": c["id"], "symbol": c["symbol"], "name": c["name"]} for c in data]

    async def fetch_coin_history(self, coin_id: str, days: str = "max") -> pd.DataFrame:
        """Fetch OHLCV history for a coin."""
        data = await self._rate_limited_request(
            f"coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days}
        )

        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        market_caps = data.get("market_caps", [])

        df = pd.DataFrame({
            "timestamp": [p[0] for p in prices],
            "price": [p[1] for p in prices],
            "volume": [v[1] for v in volumes] if volumes else [0] * len(prices),
            "market_cap": [m[1] for m in market_caps] if market_caps else [0] * len(prices)
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    async def close(self):
        await self.client.aclose()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_coingecko_client.py -v
```
Expected: PASS (requires network connectivity)

**Step 5: Commit**

```bash
git add shared/coingecko_client.py tests/test_coingecko_client.py
git commit -m "feat: add CoinGecko API client with rate limiting"
```

---

### Task 2: Training Data Collector

**Files:**
- Create: `training/collect_training_data.py`
- Create: `tests/test_collect_training_data.py`

**Step 1: Write failing test**

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_collect_training_data.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import asyncio
import pandas as pd
from pathlib import Path
from typing import List
from shared.coingecko_client import CoinGeckoClient

class TrainingDataCollector:
    def __init__(self, output_dir: Path = None, coin_limit: int = 50):
        self.output_dir = output_dir or Path(__file__).parent / "data" / "raw"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.coin_limit = coin_limit
        self.client = CoinGeckoClient()

    async def collect(self) -> None:
        """Fetch and save data for top N coins."""
        print(f"Fetching top {self.coin_limit} coins...")
        coins = await self.client.fetch_top_coins(self.coin_limit)

        for i, coin in enumerate(coins, 1):
            print(f"[{i}/{len(coins)}] Fetching {coin['name']} ({coin['id']})...")
            try:
                df = await self.client.fetch_coin_history(coin['id'])
                self._save_raw_data(coin['id'], df)
            except Exception as e:
                print(f"Error fetching {coin['id']}: {e}")

        await self.client.close()
        print("Data collection complete.")

    def _save_raw_data(self, coin_id: str, df: pd.DataFrame) -> None:
        """Save raw data to CSV."""
        df.to_csv(self.output_dir / f"{coin_id}_history.csv", index=False)

async def main():
    collector = TrainingDataCollector()
    await collector.collect()

if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_collect_training_data.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add training/collect_training_data.py tests/test_collect_training_data.py
git commit -m "feat: add training data collector script"
```

---

## Phase 2: Feature Engineering

### Task 3: Market Feature Engine

**Files:**
- Create: `shared/feature_engine.py`
- Create: `tests/test_feature_engine.py`

**Step 1: Write failing test**

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_feature_engine.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import pandas as pd
import numpy as np
import talib

class MarketFeatureEngine:
    """Engineer technical indicators from OHLCV data."""

    REQUIRED_COLS = ["timestamp", "open", "high", "low", "close", "volume"]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform OHLCV DataFrame with technical indicators.
        Drops rows with NaN values.
        """
        df = df.copy()
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Returns
        df["returns_1d"] = df["close"].pct_change() * 100
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

        # Volatility
        df["volatility_7d"] = df["log_returns"].rolling(7).std()
        df["volatility_30d"] = df["log_returns"].rolling(30).std()

        # RSI
        df["rsi_14"] = talib.RSI(df["close"], timeperiod=14)

        # MACD
        macd, macd_signal, macd_hist = talib.MACD(
            df["close"], fastperiod=12, slowperiod=26, signalperiod=9
        )
        df["macd"] = macd
        df["macd_signal"] = macd_signal
        df["macd_hist"] = macd_hist

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            df["close"], timeperiod=20, nbdevup=2, nbdevdn=2
        )
        df["bb_upper"] = bb_upper
        df["bb_lower"] = bb_lower
        df["bb_width"] = (bb_upper - bb_lower) / bb_middle

        # ATR
        df["atr_14"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)

        # OBV
        df["obv"] = talib.OBV(df["close"], df["volume"])

        # Volume ratio
        df["volume_sma_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        # Drawdown
        rolling_max = df["close"].expanding().max()
        df["drawdown"] = (df["close"] / rolling_max - 1) * 100

        # Price to SMA ratios
        df["price_sma50_ratio"] = df["close"] / df["close"].rolling(50).mean()
        df["price_sma200_ratio"] = df["close"] / df["close"].rolling(200).mean()

        # Drop NaN rows
        df = df.dropna()

        return df
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_feature_engine.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add shared/feature_engine.py tests/test_feature_engine.py
git commit -m "feat: add market feature engine with TA-Lib indicators"
```

---

### Task 4: Preprocessing Script

**Files:**
- Create: `training/preprocess.py`
- Create: `tests/test_preprocess.py`

**Step 1: Write failing test**

```python
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

    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100) * 2)

    for coin in ["bitcoin", "ethereum"]:
        df = pd.DataFrame({
            "timestamp": dates,
            "price": prices,
            "volume": np.random.randint(100000, 1000000, 100),
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_preprocess.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import pandas as pd
from pathlib import Path
from typing import List
from shared.feature_engine import MarketFeatureEngine

class Preprocessor:
    def __init__(self, raw_dir: Path = None, processed_dir: Path = None):
        self.raw_dir = raw_dir or Path(__file__).parent / "data" / "raw"
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.feature_engine = MarketFeatureEngine()

    def run(self) -> None:
        """Process all raw data files and save features."""
        print("Starting preprocessing...")

        all_features = []
        raw_files = list(self.raw_dir.glob("*_history.csv"))

        for file_path in raw_files:
            coin_id = file_path.stem.replace("_history", "")
            print(f"Processing {coin_id}...")

            df = self._load_and_convert(file_path, coin_id)
            if df is not None and len(df) > 50:
                features = self.feature_engine.transform(df)
                features["coin_id"] = coin_id
                all_features.append(features)

        if all_features:
            combined = pd.concat(all_features, ignore_index=True)
            output_path = self.processed_dir / "features.csv"
            combined.to_csv(output_path, index=False)
            print(f"Saved features to {output_path} ({len(combined)} rows)")
        else:
            print("No features generated.")

    def _load_and_convert(self, file_path: Path, coin_id: str) -> pd.DataFrame:
        """Load raw data and convert to OHLCV format."""
        try:
            df = pd.read_csv(file_path)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Convert to OHLCV (approximate from single price)
            df["open"] = df["price"].shift(1).fillna(df["price"])
            df["high"] = df["price"] * 1.01  # Approximate
            df["low"] = df["price"] * 0.99   # Approximate
            df["close"] = df["price"]
            df["volume"] = df.get("volume", 0)

            return df[["timestamp", "open", "high", "low", "close", "volume"]]
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

def main():
    preprocessor = Preprocessor()
    preprocessor.run()

if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_preprocess.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add training/preprocess.py tests/test_preprocess.py
git commit -m "feat: add preprocessing script with OHLCV conversion"
```

---

### Task 5: Label Generator

**Files:**
- Create: `training/label_generator.py`
- Create: `tests/test_label_generator.py`

**Step 1: Write failing test**

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_label_generator.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import pandas as pd
import numpy as np
from pathlib import Path

class LabelGenerator:
    """Generate risk labels from composite risk score."""

    def __init__(self, processed_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"

    def run(self) -> None:
        """Generate and add risk labels to features."""
        print("Generating risk labels...")

        features_path = self.processed_dir / "features.csv"
        df = pd.read_csv(features_path)

        df["risk_label"] = self._compute_labels(df)

        output_path = self.processed_dir / "features_with_labels.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved labeled features to {output_path}")
        print(f"Label distribution: {df['risk_label'].value_counts().sort_index().to_dict()}")

    def _compute_labels(self, df: pd.DataFrame) -> pd.Series:
        """Compute composite risk score and assign labels."""
        # Normalize features to [0, 1]
        norm_vol = self._min_max_normalize(df["volatility_30d"])
        norm_dd = self._min_max_normalize(df["drawdown"].abs())

        volume_spike = np.maximum(0, df["volume_sma_ratio"] - 1)
        norm_vs = self._min_max_normalize(volume_spike)

        # Composite score
        composite = 0.5 * norm_vol + 0.3 * norm_dd + 0.2 * norm_vs

        # Assign labels using quantiles (equal frequency)
        labels = pd.qcut(composite, q=3, labels=[0, 1, 2])
        return labels.astype(int)

    def _min_max_normalize(self, series: pd.Series) -> pd.Series:
        """Min-max normalize to [0, 1]."""
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(0, index=series.index)
        return (series - min_val) / (max_val - min_val)

def main():
    generator = LabelGenerator()
    generator.run()

if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_label_generator.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add training/label_generator.py tests/test_label_generator.py
git commit -m "feat: add risk label generator with composite scoring"
```

---

## Phase 3: Model Training

### Task 6: Risk Classifier Training

**Files:**
- Create: `training/train_risk_classifier.py`
- Create: `tests/test_train_risk_classifier.py`

**Step 1: Write failing test**

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_train_risk_classifier.py -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import xgboost as xgb

class RiskClassifierTrainer:
    """Train risk classification models."""

    FEATURE_COLS = [
        "returns_1d", "log_returns", "volatility_7d", "volatility_30d",
        "rsi_14", "macd", "macd_signal", "macd_hist",
        "bb_width", "atr_14", "obv", "volume_sma_ratio",
        "drawdown", "price_sma50_ratio", "price_sma200_ratio"
    ]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Train all risk classifiers."""
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")

        X = df[self.FEATURE_COLS].fillna(0)
        y = df["risk_label"]

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Save scaler
        joblib.dump(scaler, self.artifacts_dir / "scaler.joblib")
        print("Saved scaler.joblib")

        # Define models
        models = {
            "logreg": LogisticRegression(
                multi_class="multinomial",
                max_iter=1000,
                C=1.0,
                class_weight="balanced",
                random_state=42
            ),
            "rf": RandomForestClassifier(
                n_estimators=300,
                max_depth=10,
                min_samples_leaf=20,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            ),
            "xgb": xgb.XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="multi:softprob",
                num_class=3,
                random_state=42
            )
        }

        results = {}
        tscv = TimeSeriesSplit(n_splits=5)

        for name, model in models.items():
            print(f"\nTraining {name}...")

            # Cross-validation
            scores = cross_val_score(model, X_scaled, y, cv=tscv, scoring="f1_weighted")
            print(f"  CV F1: {scores.mean():.4f} (+/- {scores.std():.4f})")

            # Train on full data
            model.fit(X_scaled, y)

            # Save model
            joblib.dump(model, self.artifacts_dir / f"risk_{name}.joblib")
            print(f"  Saved risk_{name}.joblib")

            results[name] = scores.mean()

        # Save best model metadata
        best_model = max(results, key=results.get)
        metadata = {
            "best_model": best_model,
            "best_score": results[best_model],
            "all_scores": results,
            "features": self.FEATURE_COLS
        }
        joblib.dump(metadata, self.artifacts_dir / "risk_best.joblib")
        print(f"\nBest model: {best_model} (F1: {results[best_model]:.4f})")

def main():
    trainer = RiskClassifierTrainer()
    trainer.run()

if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_train_risk_classifier.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add training/train_risk_classifier.py tests/test_train_risk_classifier.py
git commit -m "feat: add risk classifier training (LogReg, RF, XGB)"
```

---

### Task 7: Volatility Regression Training

**Files:**
- Create: `training/train_regression.py`

**Implementation:**

```python
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
import statsmodels.api as sm

class VolatilityRegressorTrainer:
    """Train volatility regression models."""

    FEATURE_COLS = [
        "volatility_7d", "volatility_30d", "rsi_14", "atr_14",
        "bb_width", "volume_sma_ratio", "drawdown", "price_sma50_ratio", "macd_hist"
    ]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Train volatility regression models."""
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")

        # Compute target: forward 7-day volatility
        df["target_volatility"] = df["volatility_7d"].shift(-7)
        df = df.dropna(subset=["target_volatility"])

        X = df[self.FEATURE_COLS].fillna(0)
        y = df["target_volatility"]

        # Train linear regression
        print("\nTraining Linear Regression...")
        linreg = self._train_linear_regression(X, y)
        joblib.dump(linreg, self.artifacts_dir / "volatility_linreg.joblib")
        print("Saved volatility_linreg.joblib")

        # Train quantile regression at 10%, 50%, 90%
        for q in [0.1, 0.5, 0.9]:
            print(f"\nTraining Quantile Regression (q={q})...")
            qreg = self._train_quantile_regression(X, y, q)
            joblib.dump(qreg, self.artifacts_dir / f"volatility_qreg_{int(q*100)}.joblib")
            print(f"Saved volatility_qreg_{int(q*100)}.joblib")

        # Save feature list
        joblib.dump(self.FEATURE_COLS, self.artifacts_dir / "regression_features.joblib")
        print("\nRegression training complete.")

    def _train_linear_regression(self, X, y):
        """Train and evaluate linear regression."""
        tscv = TimeSeriesSplit(n_splits=5)

        mae_scores = []
        r2_scores = []

        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            model = LinearRegression()
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            mae_scores.append(mean_absolute_error(y_test, y_pred))
            r2_scores.append(r2_score(y_test, y_pred))

        print(f"  CV MAE: {np.mean(mae_scores):.6f}")
        print(f"  CV R²: {np.mean(r2_scores):.4f}")

        # Train on full data
        model = LinearRegression()
        model.fit(X, y)
        return model

    def _train_quantile_regression(self, X, y, quantile):
        """Train quantile regression model."""
        # Add constant for statsmodels
        X_const = sm.add_constant(X)

        model = sm.QuantReg(y, X_const)
        result = model.fit(q=quantile)

        print(f"  Converged: {result.mse_resid:.6f} MSE")

        return result

def main():
    trainer = VolatilityRegressorTrainer()
    trainer.run()

if __name__ == "__main__":
    main()
```

**Step 1: Create the file**

```bash
# File created above
```

**Step 2: Run the script (smoke test)**

```bash
python training/train_regression.py
```
Expected: Runs without errors (requires features_with_labels.csv)

**Step 3: Commit**

```bash
git add training/train_regression.py
git commit -m "feat: add volatility regression training (Linear + Quantile)"
```

---

### Task 8: Clustering Training

**Files:**
- Create: `training/train_clustering.py`

**Implementation:**

```python
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score

class ClusteringTrainer:
    """Train market clustering models."""

    FEATURE_COLS = [
        "volatility_7d", "volatility_30d", "returns_1d",
        "volume_sma_ratio", "rsi_14", "bb_width", "drawdown"
    ]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Train clustering models."""
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")

        X = df[self.FEATURE_COLS].fillna(0)

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        joblib.dump(scaler, self.artifacts_dir / "cluster_scaler.joblib")
        print("Saved cluster_scaler.joblib")

        # Find optimal K
        print("\nFinding optimal K...")
        best_k, best_score = self._find_optimal_k(X_scaled)
        print(f"  Best K: {best_k} (silhouette: {best_score:.4f})")

        # Train K-Means
        print("\nTraining K-Means...")
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        joblib.dump(kmeans, self.artifacts_dir / "kmeans_market.joblib")
        print("Saved kmeans_market.joblib")

        # Train Hierarchical
        print("\nTraining Hierarchical Clustering...")
        hierarchical = AgglomerativeClustering(n_clusters=best_k, linkage="ward")
        hierarchical.fit(X_scaled)
        joblib.dump(hierarchical, self.artifacts_dir / "hierarchical_market.joblib")
        print("Saved hierarchical_market.joblib")

        # Save cluster profiles
        self._save_cluster_profiles(df, X_scaled, kmeans)

        # Save feature list
        joblib.dump(self.FEATURE_COLS, self.artifacts_dir / "cluster_features.joblib")
        print("\nClustering training complete.")

    def _find_optimal_k(self, X):
        """Find optimal K using silhouette score."""
        best_k = 2
        best_score = -1

        for k in range(2, 7):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            score = silhouette_score(X, labels)
            print(f"  K={k}: silhouette={score:.4f}")

            if score > best_score:
                best_score = score
                best_k = k

        return best_k, best_score

    def _save_cluster_profiles(self, df, X_scaled, kmeans):
        """Save mean feature values per cluster."""
        df["cluster"] = kmeans.predict(X_scaled)
        profiles = df.groupby("cluster")[self.FEATURE_COLS].mean()
        profiles.to_csv(self.artifacts_dir / "cluster_profiles.csv")
        print("Saved cluster_profiles.csv")

def main():
    trainer = ClusteringTrainer()
    trainer.run()

if __name__ == "__main__":
    main()
```

**Step 1: Create the file**

```bash
# File created above
```

**Step 2: Commit**

```bash
git add training/train_clustering.py
git commit -m "feat: add clustering training (K-Means + Hierarchical)"
```

---

### Task 9: Regime Detection Training

**Files:**
- Create: `training/train_regime_model.py`

**Implementation:**

```python
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from hmmlearn.hmm import GaussianHMM
import ruptures as rpt

class RegimeModelTrainer:
    """Train regime detection models."""

    OBSERVATION_COLS = ["log_returns", "volatility_7d"]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Train regime detection models."""
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")

        # Use first coin for regime detection (time series model)
        coin = df["coin_id"].iloc[0]
        df_coin = df[df["coin_id"] == coin].sort_values("timestamp").reset_index(drop=True)

        X = df_coin[self.OBSERVATION_COLS].fillna(0).values

        # Train HMM
        print("\nTraining Hidden Markov Model...")
        hmm, regime_names = self._train_hmm(df_coin, X)
        joblib.dump(hmm, self.artifacts_dir / "regime_hmm.joblib")
        joblib.dump(regime_names, self.artifacts_dir / "regime_names.joblib")
        print("Saved regime_hmm.joblib and regime_names.joblib")

        # Detect change points
        print("\nDetecting change points...")
        change_points = self._detect_change_points(X[:, 0])  # On log_returns
        joblib.dump(change_points, self.artifacts_dir / "change_points.joblib")
        print(f"  Found {len(change_points)} change points")
        print("Saved change_points.joblib")

        print("\nRegime detection training complete.")

    def _train_hmm(self, df, X):
        """Train Gaussian HMM with optimal state selection."""
        best_n = 2
        best_bic = float("inf")
        best_model = None

        for n_states in [2, 3, 4]:
            model = GaussianHMM(
                n_components=n_states,
                covariance_type="full",
                random_state=42,
                n_iter=100
            )
            model.fit(X)

            # Calculate BIC
            log_likelihood = model.score(X)
            n_params = (n_states ** 2 - n_states) + 2 * n_states * X.shape[1] + n_states * X.shape[1] * (X.shape[1] + 1) / 2
            n_obs = len(X)
            bic = -2 * log_likelihood + n_params * np.log(n_obs)

            print(f"  n_states={n_states}: logL={log_likelihood:.2f}, BIC={bic:.2f}")

            if bic < best_bic:
                best_bic = bic
                best_n = n_states
                best_model = model

        print(f"  Selected: {best_n} states (lowest BIC)")

        # Name regimes by volatility
        hidden_states = best_model.predict(X)
        state_profiles = pd.DataFrame({
            "state": hidden_states,
            "volatility": df["volatility_7d"].values,
            "returns": df["log_returns"].values,
            "volume_ratio": df["volume_sma_ratio"].values,
            "drawdown": df["drawdown"].values
        }).groupby("state").mean()

        state_profiles = state_profiles.sort_values("volatility")
        regime_names = {
            state_profiles.index[0]: "low_vol_stable",
        }
        if len(state_profiles) > 1:
            regime_names[state_profiles.index[1]] = "moderate_transition"
        if len(state_profiles) > 2:
            regime_names[state_profiles.index[2]] = "high_vol_crisis"

        print(f"  Regimes: {regime_names}")

        return best_model, regime_names

    def _detect_change_points(self, series):
        """Detect structural breaks using PELT algorithm."""
        algo = rpt.Pelt(model="rbf", min_size=10).fit(series.reshape(-1, 1))
        change_points = algo.predict(pen=3)
        return change_points

def main():
    trainer = RegimeModelTrainer()
    trainer.run()

if __name__ == "__main__":
    main()
```

**Step 1: Create the file**

```bash
# File created above
```

**Step 2: Commit**

```bash
git add training/train_regime_model.py
git commit -m "feat: add regime detection training (HMM + PELT)"
```

---

### Task 10: PCA Training

**Files:**
- Create: `training/run_pca.py`

**Implementation:**

```python
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

class PCATrainer:
    """Train PCA for dimensionality reduction."""

    FEATURE_COLS = [
        "returns_1d", "log_returns", "volatility_7d", "volatility_30d",
        "rsi_14", "macd", "macd_signal", "macd_hist",
        "bb_width", "atr_14", "obv", "volume_sma_ratio",
        "drawdown", "price_sma50_ratio", "price_sma200_ratio"
    ]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Train PCA transformer."""
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")

        X = df[self.FEATURE_COLS].fillna(0)

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        joblib.dump(scaler, self.artifacts_dir / "pca_scaler.joblib")
        print("Saved pca_scaler.joblib")

        # Train PCA with 95% variance retention
        print("\nTraining PCA...")
        pca = PCA(n_components=0.95)
        X_pca = pca.fit_transform(X_scaled)

        print(f"  Components retained: {pca.n_components_}")
        print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.4f}")

        # Print top loadings
        print("\nTop feature loadings per component:")
        for i, component in enumerate(pca.components_[:3]):
            top_indices = np.argsort(np.abs(component))[-3:][::-1]
            top_features = [self.FEATURE_COLS[j] for j in top_indices]
            print(f"  PC{i+1}: {top_features}")

        # Save artifacts
        joblib.dump(pca, self.artifacts_dir / "pca_transformer.joblib")
        joblib.dump(self.FEATURE_COLS, self.artifacts_dir / "pca_features.joblib")
        print("\nSaved pca_transformer.joblib and pca_features.joblib")
        print("PCA training complete.")

def main():
    trainer = PCATrainer()
    trainer.run()

if __name__ == "__main__":
    main()
```

**Step 1: Create the file**

```bash
# File created above
```

**Step 2: Commit**

```bash
git add training/run_pca.py
git commit -m "feat: add PCA training with 95% variance retention"
```

---

## Phase 4: Integration

### Task 11: Full Pipeline Script

**Files:**
- Create: `training/run_all.py`

**Implementation:**

```python
#!/usr/bin/env python3
"""
Full training pipeline runner.
Executes all training scripts in sequence.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    ("Data Collection", "training/collect_training_data.py"),
    ("Preprocessing", "training/preprocess.py"),
    ("Label Generation", "training/label_generator.py"),
    ("Risk Classifier", "training/train_risk_classifier.py"),
    ("Volatility Regression", "training/train_regression.py"),
    ("Clustering", "training/train_clustering.py"),
    ("Regime Detection", "training/train_regime_model.py"),
    ("PCA", "training/run_pca.py"),
]

def run_step(name: str, script: str) -> bool:
    """Run a training step."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, script],
        cwd=Path(__file__).parent.parent
    )

    if result.returncode != 0:
        print(f"ERROR: {name} failed with code {result.returncode}")
        return False

    print(f"✓ {name} completed successfully")
    return True

def main():
    """Run complete training pipeline."""
    print("Starting Crypto Risk Lens Training Pipeline")
    print(f"{'='*60}")

    for name, script in SCRIPTS:
        if not run_step(name, script):
            print(f"\nPipeline failed at: {name}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print("Training pipeline completed successfully!")
    print(f"{'='*60}")
    print("\nGenerated artifacts:")

    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    for artifact in sorted(artifacts_dir.glob("*.joblib")):
        print(f"  - {artifact.name}")

if __name__ == "__main__":
    main()
```

**Step 1: Create the file**

```bash
# File created above
```

**Step 2: Commit**

```bash
git add training/run_all.py
git commit -m "feat: add full training pipeline runner"
```

---

## Phase 5: Documentation

### Task 12: Training README

**Files:**
- Create: `training/README.md`

**Content:**

```markdown
# Crypto Risk Lens Training Pipeline

This directory contains all scripts for training ML models for the Crypto Risk Lens backend.

## Quick Start

```bash
# Install dependencies
pip install -r ../requirements-train.txt

# Run full pipeline
python run_all.py

# Or run individual steps
python collect_training_data.py
python preprocess.py
python label_generator.py
python train_risk_classifier.py
python train_regression.py
python train_clustering.py
python train_regime_model.py
python run_pca.py
```

## Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `collect_training_data.py` | Fetch top 50 coins from CoinGecko | `data/raw/*.csv` |
| `preprocess.py` | Engineer technical indicators | `data/processed/features.csv` |
| `label_generator.py` | Compute risk labels | `data/processed/features_with_labels.csv` |
| `train_risk_classifier.py` | Train LogReg, RF, XGB | `artifacts/risk_*.joblib` |
| `train_regression.py` | Train volatility regression | `artifacts/volatility_*.joblib` |
| `train_clustering.py` | Train K-Means, Hierarchical | `artifacts/*cluster*.joblib` |
| `train_regime_model.py` | Train HMM + change points | `artifacts/regime_*.joblib` |
| `run_pca.py` | Fit PCA transformer | `artifacts/pca_*.joblib` |

## Data Flow

```
CoinGecko API
    ↓
Raw CSV files (data/raw/)
    ↓
Feature engineering (TA-Lib)
    ↓
Processed CSV (data/processed/features.csv)
    ↓
Label generation
    ↓
Processed CSV with labels
    ↓
Model training
    ↓
Joblib artifacts (artifacts/)
```

## Rate Limiting

CoinGecko free tier: 30 calls/minute
Our limit: 40 req/min (1.5s delay between requests)

## Testing

```bash
pytest tests/ -v
```
```

**Step 1: Create the file**

```bash
# File created above
```

**Step 2: Commit**

```bash
git add training/README.md
git commit -m "docs: add training pipeline README"
```

---

## Summary

This implementation plan creates a complete training pipeline with:

1. **Data Collection**: CoinGecko client with rate limiting, fetches top 50 coins
2. **Preprocessing**: OHLCV conversion, feature engineering with TA-Lib
3. **Label Generation**: Composite risk score with quantile bucketing
4. **Model Training**:
   - Risk classification (LogReg, RF, XGB)
   - Volatility regression (Linear, Quantile)
   - Market clustering (K-Means, Hierarchical)
   - Regime detection (HMM, PELT change points)
   - PCA dimensionality reduction
5. **Integration**: Full pipeline runner script
6. **Documentation**: README with usage instructions

All code is modular, testable, and follows TDD principles.

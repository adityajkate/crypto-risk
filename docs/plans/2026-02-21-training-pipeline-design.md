# Crypto Risk Lens Training Pipeline Design

**Date:** 2026-02-21
**Scope:** Training pipeline for ML models (Phase 1 of backend implementation)
**Status:** Approved

---

## 1. Overview

The training pipeline fetches historical cryptocurrency data from CoinGecko API, engineers technical indicators using TA-Lib, generates risk labels from a composite score, and trains multiple ML models. All models are saved as `.joblib` artifacts for the inference API to load.

---

## 2. Constraints

- No database - all persistence through CSV files and joblib artifacts
- Data source: CoinGecko API (free tier) for top 50 coins by market cap, maximum available history
- All API calls are realtime (no fallback mechanisms)
- Rate limiting: 40 requests/minute to respect CoinGecko free tier (30 calls/min limit + buffer)
- TimeSeriesSplit for all validation (no random shuffling)

---

## 3. Directory Structure

```
crypto-risk-lens/
├── training/
│   ├── data/
│   │   ├── raw/                    # Individual coin OHLCV CSVs
│   │   └── processed/              # Feature-engineered CSVs
│   ├── collect_training_data.py    # Fetch from CoinGecko
│   ├── preprocess.py               # Raw → processed pipeline
│   ├── label_generator.py          # Composite risk label creation
│   ├── train_risk_classifier.py    # LogReg, RF, XGB training
│   ├── train_regression.py         # Linear + Quantile regression
│   ├── train_clustering.py         # K-Means + Hierarchical
│   ├── train_regime_model.py       # HMM + change-point detection
│   └── run_pca.py                  # PCA fitting
├── shared/
│   ├── feature_engine.py           # MarketFeatureEngine class
│   └── utils.py                    # Common helpers
├── artifacts/                      # All .joblib outputs (gitignored)
└── requirements-train.txt          # Training dependencies
```

---

## 4. Data Pipeline

### 4.1 Data Collection (`collect_training_data.py`)

```
Fetch /coins/markets?order=market_cap_desc&per_page=50
    ↓
Extract 50 coin IDs
    ↓
For each coin:
  - Fetch /coins/{id}/market_chart (max days)
  - Throttle: 40 req/min to respect rate limits
  - Parse OHLCV into DataFrame
  - Save to training/data/raw/{coin_id}_history.csv
    ↓
Merge all into training/data/raw/combined_raw.csv
```

**Output Columns:** `timestamp`, `coin_id`, `open`, `high`, `low`, `close`, `volume`, `market_cap`

### 4.2 Preprocessing (`preprocess.py`)

```
Load combined_raw.csv
    ↓
Parse timestamps → Sort by (coin_id, timestamp) → Remove duplicates
    ↓
Forward-fill gaps (max 3 days per coin)
    ↓
Group by coin_id, apply MarketFeatureEngine
    ↓
Concatenate results
    ↓
Save to training/data/processed/features.csv
```

### 4.3 Label Generation (`label_generator.py`)

```
Load features.csv
    ↓
Per coin, compute composite risk score:
  normalized_volatility = min-max(volatility_30d)
  normalized_drawdown = min-max(abs(drawdown))
  volume_spike = max(0, volume_sma_ratio - 1)
  normalized_volume_spike = min-max(volume_spike)
  composite = 0.5 × vol + 0.3 × dd + 0.2 × vs
    ↓
Apply pd.qcut with 3 quantiles (equal frequency)
    ↓
Labels: 0=Low, 1=Medium, 2=High risk
    ↓
Save to training/data/processed/risk_labels.csv
```

---

## 5. Feature Engineering

### MarketFeatureEngine (`shared/feature_engine.py`)

| Feature | Computation |
|---------|-------------|
| `returns_1d` | `(close - close_prev) / close_prev * 100` |
| `log_returns` | `log(close / close_prev)` |
| `volatility_7d` | `std(log_returns, 7)` |
| `volatility_30d` | `std(log_returns, 30)` |
| `rsi_14` | `ta.RSI(close, 14)` |
| `macd`, `macd_signal`, `macd_hist` | `ta.MACD(close, 12, 26, 9)` |
| `bb_upper`, `bb_lower`, `bb_width` | `ta.BBANDS(close, 20, 2, 2)` |
| `atr_14` | `ta.ATR(high, low, close, 14)` |
| `obv` | `ta.OBV(close, volume)` |
| `volume_sma_ratio` | `volume / mean(volume, 20)` |
| `drawdown` | `(close / rolling_max(close) - 1) * 100` |
| `price_sma50_ratio` | `close / mean(close, 50)` |
| `price_sma200_ratio` | `close / mean(close, 200)` |

**Input DataFrame:** `timestamp`, `open`, `high`, `low`, `close`, `volume`
**Output:** Same DataFrame with additional columns + `risk_label`
**NaN Handling:** Drops rows with NaN values from insufficient history (e.g., first 200 rows for SMA200)

---

## 6. Model Training

### 6.1 Risk Classifier (`train_risk_classifier.py`)

**Models:**
| Model | Hyperparameters |
|-------|-----------------|
| Logistic Regression | `multinomial`, `max_iter=1000`, `C=1.0`, `class_weight=balanced` |
| Random Forest | `n_estimators=300`, `max_depth=10`, `min_samples_leaf=20`, `class_weight=balanced` |
| XGBoost | `n_estimators=300`, `max_depth=6`, `learning_rate=0.05`, `subsample=0.8`, `colsample_bytree=0.8` |

**Validation:** TimeSeriesSplit(5), weighted F1 score
**Features:** All 14 market indicators after StandardScaler
**Artifacts:**
- `risk_logreg.joblib`
- `risk_rf.joblib`
- `risk_xgb.joblib`
- `risk_best.joblib` (metadata: `{best_model: "xgb"}`)
- `scaler.joblib`

### 6.2 Volatility Regression (`train_regression.py`)

**Target:** Forward 7-day realized volatility (std of log returns shifted -7)

**Models:**
| Model | Details |
|-------|---------|
| Linear Regression | sklearn, evaluates with MAE and R² |
| Quantile Regression | statsmodels, quantiles 0.1, 0.5, 0.9 |

**Features:** `volatility_7d`, `volatility_30d`, `rsi_14`, `atr_14`, `bb_width`, `volume_sma_ratio`, `drawdown`, `price_sma50_ratio`, `macd_hist`

**Artifacts:**
- `volatility_linreg.joblib`
- `volatility_qreg_10.joblib`
- `volatility_qreg_50.joblib`
- `volatility_qreg_90.joblib`
- `regression_features.joblib`

### 6.3 Market Clustering (`train_clustering.py`)

**Models:** K-Means, Agglomerative Hierarchical (Ward)

**Features:** `volatility_7d`, `volatility_30d`, `returns_1d`, `volume_sma_ratio`, `rsi_14`, `bb_width`, `drawdown`

**Optimal K:** Iterate K=2..6, select by highest silhouette score

**Artifacts:**
- `kmeans_market.joblib`
- `hierarchical_market.joblib`
- `cluster_scaler.joblib`
- `cluster_features.joblib`
- `cluster_profiles.csv` (mean per cluster)

### 6.4 Regime Detection (`train_regime_model.py`)

**Hidden Markov Model:**
- Observation variables: `log_returns`, `volatility_7d` (2D)
- Test n_states: 2, 3, 4
- Select by lowest BIC: `-2 × log_likelihood + n_params × ln(n_obs)`
- Regime names assigned by volatility: lowest→`low_vol_stable`, middle→`moderate_transition`, highest→`high_vol_crisis`

**Change-Point Detection:**
- Library: `ruptures` with PELT algorithm
- Kernel: RBF, min_size=10, penalty=3

**Artifacts:**
- `regime_hmm.joblib`
- `regime_names.joblib`
- `change_points.joblib`

### 6.5 PCA (`run_pca.py`)

- Applied on all 14 market features after StandardScaler
- Retain components explaining 95% cumulative variance
- Print: n_components, explained variance ratios, top 3 loadings per component

**Artifacts:**
- `pca_transformer.joblib`
- `pca_scaler.joblib`
- `pca_features.joblib`

---

## 7. Dependencies

```
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
```

**System Dependency:** TA-Lib C library must be installed separately (`apt install ta-lib` or `brew install ta-lib`)

---

## 8. Execution Sequence

```bash
# Install dependencies
pip install -r requirements-train.txt

# 1. Collect training data (~10 mins with rate limiting)
python training/collect_training_data.py

# 2. Preprocess and engineer features
python training/preprocess.py

# 3. Generate risk labels
python training/label_generator.py

# 4. Train models (can run in parallel)
python training/train_risk_classifier.py
python training/train_regression.py
python training/train_clustering.py
python training/train_regime_model.py
python training/run_pca.py

# Verify artifacts
ls artifacts/
```

---

## 9. Key Design Decisions

1. **Realtime Only** - No fallback data sources; if CoinGecko API fails, script exits with error
2. **Per-Coin Caching** - Individual CSVs enable incremental updates without re-fetching all data
3. **Modular Scripts** - Each training script is standalone for flexibility and debugging
4. **TimeSeriesSplit** - Prevents data leakage by respecting temporal order in all validation
5. **Deterministic Output** - Artifact names are fixed; each run overwrites previous artifacts
6. **No Configuration File** - Hyperparameters hardcoded as constants for simplicity

---

## 10. Next Steps

After this training pipeline is complete, the inference API will be built to:
- Load all artifacts at startup
- Fetch live data from CoinGecko, CryptoPanic, Fear & Greed APIs
- Run real-time feature engineering and model inference
- Serve predictions via FastAPI endpoints

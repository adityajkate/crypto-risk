# Crypto Risk Lens

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square)
![ML](https://img.shields.io/badge/ML-XGBoost%20%7C%20RF%20%7C%20HMM-orange?style=flat-square)
![Data](https://img.shields.io/badge/Data-CoinGecko%20%7C%20CryptoPanic-purple?style=flat-square)

Real-time crypto risk assessment using four ML models in concert. You hit an endpoint with a coin ID, it fetches live candles, runs everything, and returns a risk verdict with full reasoning.

---

## How It Works

```
Live OHLCV (CoinGecko)
        │
        ▼
 Feature Engineering        ← 30+ technical indicators (TA-Lib)
        │
   ┌────┴────────────────────────────┐
   ▼         ▼           ▼          ▼
Regime    Cluster    Volatility   Risk RF
 HMM      K-Means    Regressor   Classifier
   │         │           │          │
   └────┬────────────────┘          │
        │   Regime blending         │
        └──────────────────────────►│
                                    ▼
                             Risk: low / medium / high
                             + confidence + warning
```

---

## Stack

| Layer | What |
|---|---|
| API | FastAPI + Uvicorn |
| Features | TA-Lib, pandas, numpy |
| Models | scikit-learn, XGBoost, hmmlearn, statsmodels |
| Data | CoinGecko (OHLCV), CryptoPanic (news/sentiment) |
| Artifacts | joblib serialization |

---

## Project Layout

```
crypto-risk/
├── api/
│   ├── main.py                  # all endpoints
│   ├── predictor.py             # inference engine
│   ├── coingecko_realtime.py
│   └── cryptopanic_client.py
├── shared/
│   └── feature_engine.py        # shared between training + API
├── training/
│   ├── collect_training_data.py
│   ├── preprocess.py
│   ├── label_generator.py
│   ├── train_risk_classifier.py
│   ├── train_regression.py
│   ├── train_clustering.py
│   ├── train_regime_model.py
│   └── run_all.py               # runs everything in order
└── artifacts/                   # saved .joblib models
```

---

## Data

Training data is the **top 50 coins by market cap** pulled from CoinGecko — full daily price history per coin. The raw feed is just `timestamp / price / volume`. Preprocessing converts it to OHLCV (open approximated as previous close, high/low as ±1%), then `MarketFeatureEngine` computes all indicators, and `LabelGenerator` stamps each row with a risk class.

At inference, the exact same feature engineering runs on **live candles** fetched per request. Nothing cached, nothing stale.

---

## Features

<details>
<summary><strong>Returns & Volatility</strong></summary>

| Feature | What it captures |
|---|---|
| `returns_1d` | 1-day percent price change |
| `log_returns` | log(close / prev_close) — used as HMM input |
| `volatility_7d` | 7-day rolling std of log returns |
| `volatility_30d` | 30-day rolling std — medium-term instability |

</details>

<details>
<summary><strong>Trend & Momentum</strong></summary>

| Feature | What it captures |
|---|---|
| `rsi_14` | Overbought / oversold (>70 / <30) |
| `macd` / `macd_signal` / `macd_hist` | Trend direction, signal line, acceleration |
| `stoch_rsi` | RSI of RSI — extreme momentum detection |
| `adx` | Trend strength regardless of direction |
| `cci` | Deviation from statistical mean price |
| `willr` | Williams %R — momentum oscillator |
| `roc` | Rate of change over 10 days |
| `momentum` | Raw price difference over 10 days |
| `trix` | Triple EMA ROC — filters noise |
| `ultosc` | Multi-timeframe oscillator |
| `aroon_osc` | Time since recent high vs low |
| `bop` | (close − open) / (high − low) — buyer/seller dominance |

</details>

<details>
<summary><strong>Bands, Volume & Price Position</strong></summary>

| Feature | What it captures |
|---|---|
| `bb_width` | Bollinger Band width — compression vs expansion |
| `atr_14` | Average True Range — market choppiness |
| `obv` | On-Balance Volume — volume confirms trend or diverges |
| `volume_sma_ratio` | Volume vs 20-day avg — detects abnormal spikes |
| `mfi` | Money Flow Index — RSI weighted by volume |
| `price_sma50_ratio` | Price relative to 50-day SMA |
| `price_sma200_ratio` | Long-term trend position |

</details>

<details>
<summary><strong>Drawdown</strong></summary>

| Feature | What it captures |
|---|---|
| `drawdown` | % below all-time high (expanding window) |
| `max_drawdown_30d` | Worst drawdown in last 30 days |
| `drawdown_duration` | Days continuously below −1% threshold |
| `recovery_ratio` | drawdown / max_drawdown — recovering or still falling |
| `drawdown_vol_interaction` | abs(drawdown) × volatility_30d — the dangerous combo |

</details>

<details>
<summary><strong>Regime Features</strong></summary>

| Feature | What it captures |
|---|---|
| `regime` | 0 = stable / 1 = transition / 2 = crisis (volatility quantile rules) |
| `regime_volatility_interaction` | regime × volatility_30d |
| `regime_drawdown_interaction` | regime × abs(drawdown) |

</details>

---

## Labels

Absolute thresholds — not percentiles. Percentile labeling would call a market-wide crash "low risk" because everything crashed equally.

| Class | Condition |
|---|---|
| `2` High | drawdown > 30% or 30d vol > 2% |
| `1` Medium | drawdown 15–30% or 30d vol 1–2% |
| `0` Low | everything else |

---

## Models

### Risk Classifier

Three models trained, Random Forest used at inference.

| Model | Notes |
|---|---|
| Logistic Regression | Multinomial, C=10, balanced weights |
| **Random Forest** | 500 trees, depth 20 — used in production |
| XGBoost | 300 estimators, early stopping on log-loss |

Training is strict about time series integrity — temporal 80/20 split, no shuffle, `TimeSeriesSplit` CV. Probabilities are calibrated on a holdout set using isotonic regression so that P=0.8 actually means 80%. An epsilon floor (1e-4) prevents zero-probability collapse.

### Volatility Regressor

Predicts 7-day forward volatility. Target is `volatility_7d` shifted back 7 rows.

| Model | Output |
|---|---|
| Linear Regression | Point estimate |
| QuantReg q=0.10 | Optimistic bound |
| QuantReg q=0.50 | Median |
| QuantReg q=0.90 | Risk-side bound |

The three quantiles give a confidence interval. If predicted vol expands > 2× current, it feeds back into the blending step as a risk signal.

### Market Clustering

K-Means on 7 features (`volatility_7d`, `volatility_30d`, `returns_1d`, `volume_sma_ratio`, `rsi_14`, `bb_width`, `drawdown`). Optimal K chosen by silhouette score (tested 2–6). Agglomerative with Ward linkage also trained as backup.

### Regime Detection (HMM)

Gaussian HMM on sequences of `(log_returns, volatility_7d)`. Unlike clustering, it models temporal persistence — a coin in crisis for 10 days stays weighted toward crisis more than one that had a single bad day. Number of states (2–4) picked by BIC. States named by mean volatility ordering:

- `low_vol_stable`
- `moderate_transition`
- `high_vol_crisis`

PELT change-point detection (RBF kernel) is also run on `log_returns` to find structural breaks in the series.

---

## Inference — Probability Blending

The RF classifier outputs raw probabilities. These are adjusted before the final label is assigned:

| Condition | Effect on P(low) |
|---|---|
| Regime = `high_vol_crisis` | × 0.2 |
| Regime = `moderate_transition` + (drawdown > 20% or vol > 1%) | × 0.5 |
| Predicted vol > 2× current | × 0.5 |
| Drawdown > 30% | × 0.3 |

Probabilities are re-normalized after adjustment. Final label = argmax.

A prediction is flagged **uncertain** when max confidence < 0.65 or the margin between top-2 classes < 0.10.

---

## Sample Response

```json
{
  "risk_assessment": {
    "risk_label": "high",
    "probabilities": { "low": 0.04, "medium": 0.19, "high": 0.77 },
    "confidence": 0.77,
    "is_uncertain": false,
    "regime_adjustment": "high_vol_crisis"
  },
  "volatility_forecast": {
    "predicted_volatility_7d": 0.028,
    "confidence_intervals": { "lower_10": 0.012, "median_50": 0.025, "upper_90": 0.051 }
  },
  "market_cluster": { "cluster": 2 },
  "market_regime": { "regime_name": "high_vol_crisis" }
}
```

---

## API

| Endpoint | Description |
|---|---|
| `GET /api/v1/coin/{id}/analysis` | Full analysis — risk + vol forecast + cluster + regime |
| `GET /api/v1/coin/{id}/risk` | Risk label only |
| `GET /api/v1/coin/{id}/price` | Current price + market data |
| `GET /api/v1/batch/analysis` | Up to 10 coins, comma-separated |
| `GET /api/v1/trending` | Trending from CoinGecko |
| `GET /api/v1/global` | Global market metrics |
| `GET /api/v1/news` | CryptoPanic news feed |
| `GET /api/v1/sentiment/{currency}` | Sentiment per coin |
| `GET /health` | Health check |

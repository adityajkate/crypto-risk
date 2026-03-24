# Crypto Risk Lens

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square)
![ML](https://img.shields.io/badge/ML-XGBoost%20%7C%20RF%20%7C%20HMM-orange?style=flat-square)

Real-time cryptocurrency risk assessment platform using machine learning. Analyzes live market data, news sentiment, and technical indicators to provide risk scores and predictions.

---

## Quick Start

### Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your API keys to .env

# Train models (first time only)
cd ml/scripts
python run_all.py

# Start API server
python run_api.py
# API: http://localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
# UI: http://localhost:3000
```

---

## Architecture

```
User Request (coin ID)
        ↓
┌───────────────────────────────────────┐
│  FastAPI Backend (backend/api/)       │
│  - Fetch live OHLCV from CoinGecko    │
│  - Scrape news (RSS, Reddit, Google)  │
│  - Process sentiment with LLM         │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│  Feature Engineering (core/)          │
│  - 30+ technical indicators (TA-Lib)  │
│  - RSI, MACD, Bollinger, ATR, etc.    │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│  ML Models (ml/)                      │
│  ├─ Risk Classifier (Random Forest)   │
│  ├─ Volatility Regressor (QuantReg)   │
│  ├─ Market Clustering (K-Means)       │
│  └─ Regime Detection (HMM)            │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│  Probability Blending & Adjustment    │
│  - Regime-based risk weighting        │
│  - Volatility spike detection         │
│  - Confidence scoring                 │
└───────────────────────────────────────┘
        ↓
    Risk Score: Low / Medium / High
    + Confidence + Reasoning
```

---

## Project Structure

```
crypto-risk/
├── backend/              # API & data processing
│   ├── api/
│   │   ├── main.py                    # FastAPI endpoints
│   │   ├── coingecko_realtime.py      # Live price data
│   │   ├── event_store.py             # Event storage
│   │   ├── fear_greed_client.py       # Fear & Greed Index
│   │   └── google_trends_client.py    # Google Trends data
│   ├── scrapers/
│   │   ├── layer_a.py                 # RSS/Reddit scrapers
│   │   └── layer_b.py                 # Google News scraper
│   ├── services/
│   │   └── llm_summarizer.py          # LLM sentiment analysis
│   └── workers/
│       ├── clustering_worker.py       # Background clustering
│       └── sentiment_worker.py        # Sentiment processing
│
├── core/                 # Shared utilities
│   ├── coin_metadata.py              # Coin mapping & metadata
│   ├── coingecko_client.py           # CoinGecko API client
│   ├── feature_engine.py             # Technical indicators
│   └── models.py                     # Data models
│
├── ml/                   # Machine learning
│   ├── scripts/
│   │   ├── collect_training_data.py  # Data collection
│   │   ├── preprocess.py             # Data preprocessing
│   │   ├── label_generator.py        # Risk labels
│   │   ├── train_risk_classifier.py  # Risk model
│   │   ├── train_regression.py       # Volatility forecasting
│   │   ├── train_clustering.py       # Market clustering
│   │   ├── train_regime_model.py     # HMM regime detection
│   │   └── run_all.py                # Full training pipeline
│   └── data/                         # Training data storage
│
├── frontend/             # React + TypeScript UI
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx       # Home page
│   │   │   ├── Dashboard.tsx         # Main dashboard
│   │   │   ├── SentimentPage.tsx     # Sentiment analysis
│   │   │   └── TopCoinsPage.tsx      # Top coins view
│   │   ├── components/               # Reusable components
│   │   ├── services/
│   │   │   └── apiClient.ts          # API integration
│   │   └── context/
│   │       └── CryptoContext.tsx     # Global state
│   └── ...
│
└── models/               # Trained model artifacts (.joblib)
```

---

## Code Workflow

### 1. Data Collection (`ml/scripts/collect_training_data.py`)

- Fetches top 50 coins by market cap from CoinGecko
- Downloads full price history (timestamp, price, volume)
- Saves raw data to `ml/data/raw/`

### 2. Preprocessing (`ml/scripts/preprocess.py`)

- Converts raw data to OHLCV format
- Approximates open/high/low from close prices
- Applies feature engineering via [`MarketFeatureEngine`](core/feature_engine.py)
- Generates 30+ technical indicators

### 3. Label Generation (`ml/scripts/label_generator.py`)

- Assigns risk labels based on absolute thresholds:
  - **High (2)**: drawdown > 30% OR 30d volatility > 2%
  - **Medium (1)**: drawdown 15-30% OR 30d volatility 1-2%
  - **Low (0)**: everything else

### 4. Model Training (`ml/scripts/train_*.py`)

- **Risk Classifier**: Random Forest (500 trees, depth 20)
- **Volatility Regressor**: Quantile regression (10th, 50th, 90th percentiles)
- **Market Clustering**: K-Means on 7 key features
- **Regime Detection**: Gaussian HMM on log returns + volatility
- Models saved to `models/` directory

### 5. API Inference (`backend/api/main.py`)

When a request comes in:

1. Fetch live OHLCV data from CoinGecko
2. Run feature engineering (same as training)
3. Load trained models and predict
4. Blend probabilities based on regime/volatility
5. Return risk score + confidence + reasoning

### 6. Background Workers (`backend/workers/`)

- **Sentiment Worker**: Scrapes news, processes with LLM
- **Clustering Worker**: Updates market clusters periodically

### 7. Frontend (`frontend/src/`)

- Displays risk scores, charts, and sentiment
- Real-time updates via API polling
- Interactive visualizations with React + TypeScript

---

## Key Features

### Technical Indicators (30+)

- **Trend**: RSI, MACD, ADX, CCI, Aroon
- **Volatility**: Bollinger Bands, ATR, Standard Deviation
- **Volume**: OBV, MFI, Volume Ratio
- **Momentum**: Stochastic RSI, Williams %R, ROC
- **Drawdown**: Max drawdown, recovery ratio, duration

### ML Models

- **Risk Classifier**: Predicts low/medium/high risk with confidence
- **Volatility Forecaster**: 7-day forward volatility with confidence intervals
- **Market Clustering**: Groups coins by behavior patterns
- **Regime Detection**: Identifies stable/transition/crisis states

### Sentiment Analysis

- Scrapes RSS feeds, Reddit, Google News
- LLM-powered sentiment scoring
- Fear & Greed Index integration
- Google Trends correlation

---

## API Endpoints

| Endpoint                           | Description                                          |
| ---------------------------------- | ---------------------------------------------------- |
| `GET /api/v1/coin/{id}/analysis`   | Full analysis (risk + volatility + cluster + regime) |
| `GET /api/v1/coin/{id}/risk`       | Risk assessment only                                 |
| `GET /api/v1/coin/{id}/price`      | Current price + market data                          |
| `GET /api/v1/batch/analysis`       | Batch analysis (up to 10 coins)                      |
| `GET /api/v1/sentiment/{currency}` | Sentiment analysis for coin                          |
| `GET /api/v1/trending`             | Trending coins from CoinGecko                        |
| `GET /api/v1/global`               | Global market metrics                                |
| `GET /health`                      | Health check                                         |

---

## Example Response

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
    "confidence_intervals": {
      "lower_10": 0.012,
      "median_50": 0.025,
      "upper_90": 0.051
    }
  },
  "market_cluster": { "cluster": 2 },
  "market_regime": { "regime_name": "high_vol_crisis" }
}
```

---

## Tech Stack

- **Backend**: FastAPI, Uvicorn, Python 3.10+
- **ML**: scikit-learn, XGBoost, hmmlearn, TA-Lib
- **Data**: CoinGecko API, RSS feeds, Reddit API, Google News
- **Frontend**: React, TypeScript, Vite
- **Storage**: In-memory event store, joblib model serialization

---

## Environment Variables

Create a [`.env`](.env.example) file:

```bash
COINGECKO_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  # For LLM sentiment
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
```

---

## License

MIT

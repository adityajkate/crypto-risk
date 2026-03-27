<h1 align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=32&duration=3000&pause=1000&color=6366F1&center=true&vCenter=true&width=600&lines=Crypto+Risk+Lens;Real-Time+Risk+Assessment;ML-Powered+Analytics" alt="Crypto Risk Lens" />
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19.2-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/ML-XGBoost%20%7C%20RF-FF6F00?style=for-the-badge&logo=scikit-learn&logoColor=white" alt="ML" />
</p>

<p align="center">
  <strong>Real-time cryptocurrency risk assessment platform powered by machine learning</strong><br>
  Analyzes live market data, news sentiment, and technical indicators to provide actionable risk scores
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#api-endpoints">API</a> •
  <a href="#tech-stack">Tech Stack</a>
</p>

---

## Features

<table>
<tr>
<td width="50%">

### Risk Assessment
- **Multi-Model Ensemble**: Random Forest + XGBoost + HMM
- **Real-time Analysis**: Live OHLCV data from CoinGecko
- **Confidence Scoring**: Uncertainty quantification
- **Regime Detection**: Market state identification

</td>
<td width="50%">

### Technical Analysis
- **30+ Indicators**: RSI, MACD, Bollinger, ATR, etc.
- **Volatility Forecasting**: 7-day predictions with CI
- **Market Clustering**: Behavioral pattern grouping
- **Drawdown Metrics**: Risk exposure tracking

</td>
</tr>
<tr>
<td width="50%">

### Sentiment Analysis
- **Multi-Source Scraping**: RSS, Reddit, Google News
- **CryptoBERT**: Transformer-based sentiment scoring
- **NLP Summarization**: Extractive text analysis
- **Fear & Greed Index**: Market emotion tracking
- **Google Trends**: Search volume correlation

</td>
<td width="50%">

### Modern UI
- **Interactive Dashboard**: Real-time visualizations
- **3D Globe**: Global market overview
- **Responsive Design**: Mobile-first approach
- **Smooth Animations**: Motion-powered transitions

</td>
</tr>
</table>

---

## Quick Start

### Prerequisites

```bash
Python 3.10+  |  Node.js 18+  |  npm/yarn
```

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/adityajkate/crypto-risk.git
cd crypto-risk

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Add your API keys to .env

# Train ML models (first time only)
cd ml/scripts
python run_all.py

# Start the API server
cd ../..
python run_api.py
```

**API Server**: http://localhost:8000

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**UI Dashboard**: http://localhost:3000

---

## Architecture

<p align="center">
  <img src="https://img.shields.io/badge/Data%20Flow-Live%20Data%20→%20Feature%20Engineering%20→%20ML%20Inference%20→%20Risk%20Score%20→%20Visualization-blue?style=for-the-badge" alt="Data Flow" />
</p>

### Components

1. **Data Collection**: Fetch top coins from CoinGecko
2. **Preprocessing**: Convert to OHLCV format + feature engineering
3. **Label Generation**: Assign risk labels based on thresholds
4. **Model Training**: Train ensemble of ML models
5. **API Inference**: Real-time predictions via FastAPI
6. **Background Workers**: Sentiment analysis + clustering updates
7. **Frontend Display**: Interactive visualizations

---

## Project Structure

```
crypto-risk/
├── backend/              # FastAPI application
│   ├── api/              # API endpoints & clients
│   ├── scrapers/         # News & social media scrapers
│   ├── services/         # NLP & business logic
│   └── workers/          # Background processing
├── ml/                   # Machine learning pipeline
│   ├── scripts/          # Training & preprocessing
│   └── data/             # Training datasets
├── core/                 # Shared utilities
│   ├── feature_engine.py # Technical indicators
│   ├── coingecko_client.py # API client
│   └── models.py         # Data models
├── frontend/             # React + TypeScript UI
│   └── src/
│       ├── pages/        # Route components
│       ├── components/   # Reusable UI components
│       └── services/     # API integration
└── models/               # Trained model artifacts
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/coin/{id}/analysis` | Full risk analysis (risk + volatility + cluster + regime) |
| `GET` | `/api/v1/coin/{id}/risk` | Risk assessment only |
| `GET` | `/api/v1/coin/{id}/price` | Current price & market data |
| `GET` | `/api/v1/batch/analysis` | Batch analysis (up to 10 coins) |
| `GET` | `/api/v1/sentiment/{currency}` | Sentiment analysis for coin |
| `GET` | `/api/v1/trending` | Trending coins from CoinGecko |
| `GET` | `/api/v1/global` | Global market metrics |
| `GET` | `/health` | Health check |

### Example Response

```json
{
  "risk_assessment": {
    "risk_label": "high",
    "probabilities": {
      "low": 0.04,
      "medium": 0.19,
      "high": 0.77
    },
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

### Backend
- **Framework**: FastAPI 0.104, Uvicorn
- **ML**: scikit-learn, XGBoost, hmmlearn, statsmodels
- **Analysis**: TA-Lib (30+ technical indicators)
- **NLP**: Transformers, PyTorch, Sentence-Transformers
- **Data**: pandas, numpy, httpx, aiohttp

### Frontend
- **Framework**: React 19.2, TypeScript 5.8
- **Build**: Vite 6.2
- **3D Graphics**: Three.js, React Three Fiber
- **Charts**: Recharts, D3.js
- **Animation**: Motion (Framer Motion)
- **UI**: Lucide Icons, Rough Notation

### Data Sources
- **Market Data**: CoinGecko API
- **Sentiment**: RSS feeds, Reddit API, Google News (CryptoBERT + NLP)
- **Trends**: Google Trends (pytrends)
- **Metrics**: Fear & Greed Index

---

## Environment Variables

Create a `.env` file in the root directory:

```bash
# CoinGecko API
COINGECKO_API_KEY=your_coingecko_key

# Google API (optional - only for Google Trends)
# GOOGLE_API_KEY=your_google_key

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Rate Limiting
RATE_LIMIT_DELAY=1.0
```

---

## ML Models

<p align="center">
  <img src="https://img.shields.io/badge/Random%20Forest-500%20trees-success?style=flat-square" alt="RF" />
  <img src="https://img.shields.io/badge/XGBoost-Gradient%20Boosting-orange?style=flat-square" alt="XGB" />
  <img src="https://img.shields.io/badge/HMM-Regime%20Detection-blue?style=flat-square" alt="HMM" />
  <img src="https://img.shields.io/badge/K--Means-Clustering-purple?style=flat-square" alt="KMeans" />
</p>

### 1. Risk Classifier
- **Algorithm**: Random Forest (500 trees, depth 20)
- **Output**: Low / Medium / High risk with probabilities
- **Features**: 30+ technical indicators

### 2. Volatility Forecaster
- **Algorithm**: Quantile Regression
- **Output**: 7-day forward volatility with confidence intervals
- **Quantiles**: 10th, 50th, 90th percentiles

### 3. Market Clustering
- **Algorithm**: K-Means
- **Output**: Behavioral pattern groups
- **Features**: 7 key market indicators

### 4. Regime Detection
- **Algorithm**: Gaussian Hidden Markov Model
- **Output**: Market state (stable/transition/crisis)
- **Features**: Log returns + volatility

---

## Technical Indicators

<details>
<summary><strong>View All Indicators (30+)</strong></summary>

### Trend Indicators
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- ADX (Average Directional Index)
- CCI (Commodity Channel Index)
- Aroon Oscillator

### Volatility Indicators
- Bollinger Bands (Upper, Middle, Lower)
- ATR (Average True Range)
- Standard Deviation
- Historical Volatility

### Volume Indicators
- OBV (On-Balance Volume)
- MFI (Money Flow Index)
- Volume Ratio
- VWAP (Volume Weighted Average Price)

### Momentum Indicators
- Stochastic RSI
- Williams %R
- ROC (Rate of Change)
- Momentum Oscillator

### Risk Metrics
- Maximum Drawdown
- Recovery Ratio
- Drawdown Duration
- Sharpe Ratio

</details>

---

## Training Pipeline

```bash
# Full training pipeline
cd ml/scripts
python run_all.py

# Individual steps
python collect_training_data.py  # Fetch historical data
python preprocess.py             # Feature engineering
python label_generator.py        # Generate risk labels
python train_risk_classifier.py  # Train risk model
python train_regression.py       # Train volatility model
python train_clustering.py       # Train clustering model
python train_regime_model.py     # Train regime detector
```

---

## Contributors

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/adityajkate">
        <img src="https://img.shields.io/badge/Aditya%20Kate-Developer-blue?style=for-the-badge" alt="Aditya Kate" />
      </a>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/Tanmay%20Harmalkar-Developer-green?style=for-the-badge" alt="Tanmay Harmalkar" />
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/Suman%20Manik-Developer-orange?style=for-the-badge" alt="Suman Manik" />
    </td>
  </tr>
</table>

---

## License

This project is licensed under the MIT License.

---

<p align="center">
  <a href="https://github.com/adityajkate/crypto-risk">
    <img src="https://img.shields.io/github/stars/adityajkate/crypto-risk?style=social" alt="Stars" />
  </a>
  <a href="https://github.com/adityajkate/crypto-risk/issues">
    <img src="https://img.shields.io/github/issues/adityajkate/crypto-risk?style=flat-square" alt="Issues" />
  </a>
  <a href="https://github.com/adityajkate/crypto-risk/network/members">
    <img src="https://img.shields.io/github/forks/adityajkate/crypto-risk?style=social" alt="Forks" />
  </a>
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=14&duration=3000&pause=1000&color=6366F1&center=true&vCenter=true&width=600&lines=Built+with+precision+and+passion;Empowering+crypto+traders+with+AI;Star+this+repo+if+you+find+it+useful" alt="Footer" />
</p>

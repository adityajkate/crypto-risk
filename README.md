# Crypto Risk Lens 🔍

**Real-time cryptocurrency risk analysis powered by machine learning.**

A complete ML pipeline and REST API for analyzing cryptocurrency risk using real-time market data, technical indicators, and trained models.

## 🎯 Features

### Training Pipeline
- **Data Collection**: Fetch historical data from CoinGecko API
- **Feature Engineering**: 17 technical indicators using TA-Lib
- **Risk Classification**: Multi-class risk prediction (low/medium/high)
- **Volatility Forecasting**: Linear and quantile regression models
- **Market Clustering**: K-Means and Hierarchical clustering
- **Regime Detection**: Hidden Markov Models for market state identification
- **Dimensionality Reduction**: PCA with 95% variance retention

### REST API
- **Real-time Analysis**: Live risk assessment for any cryptocurrency
- **Batch Processing**: Analyze multiple coins simultaneously
- **News & Sentiment**: Integration with CryptoPanic for market sentiment
- **Global Market Data**: Track overall market conditions
- **Interactive Docs**: Swagger UI for easy API exploration

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd crypto-risk

# Install training dependencies
pip install -r requirements-train.txt

# Install API dependencies
pip install -r requirements-api.txt
```

### 1. Train the Models

```bash
# Run the complete training pipeline
python training/run_all.py
```

This will:
1. Fetch data for top 10 cryptocurrencies (365 days)
2. Generate technical indicators
3. Create risk labels
4. Train 8 different ML models
5. Save artifacts to `artifacts/` directory

**Time**: ~2-3 minutes (due to API rate limiting)

### 2. Configure API Keys (Optional)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

```env
COINGECKO_API_KEY=your_coingecko_api_key_here
CRYPTOPANIC_API_KEY=your_cryptopanic_api_key_here
```

**Note**: API keys are optional. The system works with free tier APIs.

### 3. Start the API

```bash
python run_api.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs

## 📊 Usage Examples

### Analyze a Cryptocurrency

```bash
curl http://localhost:8000/api/v1/coin/bitcoin/analysis?days=30
```

**Response:**
```json
{
  "success": true,
  "data": {
    "coin_id": "bitcoin",
    "current_price": {
      "current_price": 50000,
      "market_cap": 950000000000
    },
    "risk_analysis": {
      "risk_assessment": {
        "risk_level": 1,
        "risk_label": "medium",
        "confidence": 0.55
      },
      "volatility_forecast": {
        "predicted_volatility_7d": 0.035
      },
      "market_regime": {
        "regime_name": "low_vol_stable"
      }
    }
  }
}
```

### Get Trending Coins

```bash
curl http://localhost:8000/api/v1/trending
```

### Batch Analysis

```bash
curl "http://localhost:8000/api/v1/batch/analysis?coin_ids=bitcoin,ethereum,ripple&days=30"
```

### Get News & Sentiment

```bash
curl http://localhost:8000/api/v1/news?currencies=BTC,ETH&limit=10
curl http://localhost:8000/api/v1/sentiment/BTC
```

## 📁 Project Structure

```
crypto-risk/
├── api/                          # FastAPI application
│   ├── main.py                   # API endpoints
│   ├── config.py                 # Configuration
│   ├── coingecko_realtime.py     # Real-time data client
│   ├── cryptopanic_client.py     # News & sentiment client
│   └── predictor.py              # ML model inference
│
├── training/                     # Training pipeline
│   ├── collect_training_data.py  # Data collection
│   ├── preprocess.py             # Feature engineering
│   ├── label_generator.py        # Risk label generation
│   ├── train_risk_classifier.py  # Risk classification models
│   ├── train_regression.py       # Volatility regression
│   ├── train_clustering.py       # Market clustering
│   ├── train_regime_model.py     # Regime detection
│   ├── run_pca.py                # PCA dimensionality reduction
│   ├── run_all.py                # Full pipeline runner
│   └── README.md                 # Training documentation
│
├── shared/                       # Shared utilities
│   ├── coingecko_client.py       # Training data client
│   └── feature_engine.py         # Feature engineering
│
├── tests/                        # Test suite
│   └── test_*.py                 # Unit tests
│
├── artifacts/                    # Trained models (generated)
│   └── *.joblib                  # Model files
│
├── requirements-train.txt        # Training dependencies
├── requirements-api.txt          # API dependencies
├── run_api.py                    # API startup script
├── API_README.md                 # API documentation
└── README.md                     # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_coingecko_client.py -v
```

## 🔧 Configuration

### Training Pipeline

Edit `training/collect_training_data.py` to change:
- Number of coins: `coin_limit` parameter (default: 10)
- Historical data period: Limited to 365 days on free tier

### API Settings

Edit `.env` file:
```env
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
RATE_LIMIT_DELAY=1.0
```

## 📈 Models & Algorithms

### Risk Classification
- **Logistic Regression**: Baseline model
- **Random Forest**: Best performer (F1: 0.80)
- **XGBoost**: Gradient boosting ensemble

### Volatility Forecasting
- **Linear Regression**: Point estimates
- **Quantile Regression**: Confidence intervals (10%, 50%, 90%)

### Market Analysis
- **K-Means Clustering**: Market regime identification
- **Hierarchical Clustering**: Alternative clustering approach
- **Hidden Markov Model**: Temporal regime detection
- **PELT Algorithm**: Structural break detection

### Feature Engineering
17 technical indicators:
- Returns & Log Returns
- Volatility (7-day, 30-day)
- RSI, MACD, Bollinger Bands
- ATR, OBV, Volume ratios
- Drawdown, SMA ratios

## 🌐 API Endpoints

### Core Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /api/v1/coin/{coin_id}/analysis` - Comprehensive analysis
- `GET /api/v1/coin/{coin_id}/risk` - Risk assessment only
- `GET /api/v1/coin/{coin_id}/price` - Current price data

### Market Data
- `GET /api/v1/trending` - Trending coins
- `GET /api/v1/global` - Global market statistics
- `GET /api/v1/batch/analysis` - Batch analysis

### News & Sentiment (Requires API Key)
- `GET /api/v1/news` - Crypto news
- `GET /api/v1/sentiment/{currency}` - Sentiment analysis

See [API_README.md](API_README.md) for detailed documentation.

## 🔑 API Keys

### CoinGecko (Optional)
- **Free Tier**: Works without API key (limited rate)
- **Pro Tier**: Higher limits, more data
- Get key: https://www.coingecko.com/en/api/pricing

### CryptoPanic (Required for News)
- **Free**: 100 calls/day
- **Pro**: Unlimited calls
- Get key: https://cryptopanic.com/developers/api/

## 🚢 Production Deployment

### Using Uvicorn

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements-api.txt requirements-train.txt ./
RUN pip install -r requirements-api.txt

COPY . .

# Train models (or mount pre-trained artifacts)
RUN python training/run_all.py

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 Performance

### Training Pipeline
- **Data Collection**: ~1-2 minutes (10 coins, rate limited)
- **Feature Engineering**: ~5 seconds
- **Model Training**: ~10-15 seconds
- **Total**: ~2-3 minutes

### API Response Times
- **Single Coin Analysis**: ~2-3 seconds
- **Batch Analysis (10 coins)**: ~15-20 seconds
- **Price Data Only**: <1 second

## 🛠️ Development

### Project Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-train.txt
pip install -r requirements-api.txt

# Run tests
pytest tests/ -v
```

### Adding New Features

1. **New Technical Indicator**: Edit `shared/feature_engine.py`
2. **New Model**: Create script in `training/`
3. **New API Endpoint**: Edit `api/main.py`

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📧 Support

For issues or questions:
- Check the [API Documentation](API_README.md)
- Review the [Training Pipeline README](training/README.md)
- Open an issue on GitHub

## 🎓 Credits

Built with:
- **FastAPI**: Modern web framework
- **scikit-learn**: Machine learning models
- **XGBoost**: Gradient boosting
- **TA-Lib**: Technical analysis
- **CoinGecko API**: Market data
- **CryptoPanic API**: News & sentiment

---

**Made with ❤️ for the crypto community**

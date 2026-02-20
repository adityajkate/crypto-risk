# Crypto Risk Lens API

Real-time cryptocurrency risk analysis API with ML-powered predictions.

## Features

- **Real-time Price Data**: Live cryptocurrency prices from CoinGecko
- **Risk Assessment**: ML-based risk classification (low/medium/high)
- **Volatility Forecasting**: Predict future volatility with confidence intervals
- **Market Regime Detection**: Identify current market conditions using HMM
- **Market Clustering**: Classify coins into market behavior clusters
- **News & Sentiment**: Real-time crypto news and sentiment analysis from CryptoPanic
- **Batch Analysis**: Analyze multiple coins in a single request

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-api.txt
```

### 2. Configure API Keys (Optional)

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
COINGECKO_API_KEY=your_coingecko_api_key_here
CRYPTOPANIC_API_KEY=your_cryptopanic_api_key_here
```

**Note**: API keys are optional. The API will work with CoinGecko's free tier if no key is provided. CryptoPanic features require an API key.

### 3. Ensure Models are Trained

Make sure you have trained models in the `artifacts/` directory:

```bash
python training/run_all.py
```

### 4. Start the API

```bash
python run_api.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health & Status

- `GET /` - API information
- `GET /health` - Health check

### Coin Analysis

- `GET /api/v1/coin/{coin_id}/price` - Get current price and market data
- `GET /api/v1/coin/{coin_id}/analysis` - Comprehensive risk analysis
- `GET /api/v1/coin/{coin_id}/risk` - Risk assessment only

**Example:**
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
      "market_cap": 950000000000,
      "price_change_24h": 1250.50
    },
    "risk_analysis": {
      "risk_assessment": {
        "risk_level": 1,
        "risk_label": "medium",
        "probabilities": {
          "low": 0.25,
          "medium": 0.55,
          "high": 0.20
        },
        "confidence": 0.55
      },
      "volatility_forecast": {
        "predicted_volatility_7d": 0.035,
        "confidence_intervals": {
          "lower_10": 0.020,
          "median_50": 0.033,
          "upper_90": 0.048
        }
      },
      "market_cluster": {
        "cluster": 0,
        "cluster_name": "market_regime_0"
      },
      "market_regime": {
        "regime_state": 0,
        "regime_name": "low_vol_stable",
        "description": "Low volatility, stable market conditions"
      }
    }
  },
  "timestamp": "2026-02-20T19:56:18.175Z"
}
```

### Market Data

- `GET /api/v1/trending` - Get trending coins
- `GET /api/v1/global` - Global market statistics

### Batch Analysis

- `GET /api/v1/batch/analysis?coin_ids=bitcoin,ethereum,ripple&days=30` - Analyze multiple coins

### News & Sentiment (Requires CryptoPanic API Key)

- `GET /api/v1/news?currencies=BTC,ETH&filter_type=hot&limit=20` - Get crypto news
- `GET /api/v1/sentiment/{currency}` - Get sentiment analysis for a coin

**Example:**
```bash
curl http://localhost:8000/api/v1/sentiment/BTC
```

## API Parameters

### Common Parameters

- `coin_id`: CoinGecko coin ID (e.g., `bitcoin`, `ethereum`, `ripple`)
- `days`: Historical data period (7-365 days, default: 30)
- `limit`: Number of results (1-100, default: 20)

### News Filters

- `hot`: Trending news
- `rising`: Rising in popularity
- `bullish`: Positive sentiment
- `bearish`: Negative sentiment
- `important`: Community-marked important news

## Getting API Keys

### CoinGecko API Key (Optional)

1. Visit https://www.coingecko.com/en/api/pricing
2. Sign up for a free or paid plan
3. Get your API key from the dashboard
4. Add to `.env`: `COINGECKO_API_KEY=your_key`

**Benefits:**
- Higher rate limits
- Access to more historical data
- Priority support

### CryptoPanic API Key (Required for News)

1. Visit https://cryptopanic.com/developers/api/
2. Sign up for a free account
3. Get your API token
4. Add to `.env`: `CRYPTOPANIC_API_KEY=your_key`

## Rate Limits

- **CoinGecko Free**: 10-50 calls/minute
- **CoinGecko Pro**: 500+ calls/minute
- **CryptoPanic Free**: 100 calls/day
- **CryptoPanic Pro**: Unlimited calls

The API automatically handles rate limiting with configurable delays.

## Architecture

```
api/
├── main.py                    # FastAPI application
├── config.py                  # Configuration settings
├── coingecko_realtime.py      # CoinGecko client
├── cryptopanic_client.py      # CryptoPanic client
└── predictor.py               # ML model inference

shared/
├── coingecko_client.py        # Training data client
└── feature_engine.py          # Feature engineering

artifacts/                     # Trained ML models
└── *.joblib
```

## Development

### Run with Auto-reload

```bash
python run_api.py
```

### Run Tests

```bash
pytest tests/ -v
```

### Access Interactive Docs

Visit http://localhost:8000/docs for Swagger UI with interactive API testing.

## Production Deployment

### Using Uvicorn

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```env
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
RATE_LIMIT_DELAY=1.0
```

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Resource not found
- `500`: Internal server error
- `503`: Service unavailable (missing API key)

Error response format:
```json
{
  "detail": "Error message here"
}
```

## Support

For issues or questions:
- Check the interactive docs at `/docs`
- Review the training pipeline README in `training/README.md`
- Ensure models are trained before starting the API

## License

MIT License

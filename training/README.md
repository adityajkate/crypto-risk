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

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

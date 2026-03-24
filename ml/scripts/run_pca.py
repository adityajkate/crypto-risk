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
        self.processed_dir = processed_dir or Path(__file__).parent.parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent.parent / "models"
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

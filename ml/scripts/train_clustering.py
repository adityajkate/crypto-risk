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
        self.processed_dir = processed_dir or Path(__file__).parent.parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent.parent / "models"
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

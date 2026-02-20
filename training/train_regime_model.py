import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from hmmlearn.hmm import GaussianHMM
import ruptures as rpt

class RegimeModelTrainer:
    """Train regime detection models."""

    OBSERVATION_COLS = ["log_returns", "volatility_7d"]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Train regime detection models."""
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")

        # Use first coin for regime detection (time series model)
        coin = df["coin_id"].iloc[0]
        df_coin = df[df["coin_id"] == coin].sort_values("timestamp").reset_index(drop=True)

        X = df_coin[self.OBSERVATION_COLS].fillna(0).values

        # Train HMM
        print("\nTraining Hidden Markov Model...")
        hmm, regime_names = self._train_hmm(df_coin, X)
        joblib.dump(hmm, self.artifacts_dir / "regime_hmm.joblib")
        joblib.dump(regime_names, self.artifacts_dir / "regime_names.joblib")
        print("Saved regime_hmm.joblib and regime_names.joblib")

        # Detect change points
        print("\nDetecting change points...")
        change_points = self._detect_change_points(X[:, 0])  # On log_returns
        joblib.dump(change_points, self.artifacts_dir / "change_points.joblib")
        print(f"  Found {len(change_points)} change points")
        print("Saved change_points.joblib")

        print("\nRegime detection training complete.")

    def _train_hmm(self, df, X):
        """Train Gaussian HMM with optimal state selection."""
        best_n = 2
        best_bic = float("inf")
        best_model = None

        for n_states in [2, 3, 4]:
            model = GaussianHMM(
                n_components=n_states,
                covariance_type="full",
                random_state=42,
                n_iter=100
            )
            model.fit(X)

            # Calculate BIC
            log_likelihood = model.score(X)
            n_params = (n_states ** 2 - n_states) + 2 * n_states * X.shape[1] + n_states * X.shape[1] * (X.shape[1] + 1) / 2
            n_obs = len(X)
            bic = -2 * log_likelihood + n_params * np.log(n_obs)

            print(f"  n_states={n_states}: logL={log_likelihood:.2f}, BIC={bic:.2f}")

            if bic < best_bic:
                best_bic = bic
                best_n = n_states
                best_model = model

        print(f"  Selected: {best_n} states (lowest BIC)")

        # Name regimes by volatility
        hidden_states = best_model.predict(X)
        state_profiles = pd.DataFrame({
            "state": hidden_states,
            "volatility": df["volatility_7d"].values,
            "returns": df["log_returns"].values,
            "volume_ratio": df["volume_sma_ratio"].values,
            "drawdown": df["drawdown"].values
        }).groupby("state").mean()

        state_profiles = state_profiles.sort_values("volatility")
        regime_names = {
            state_profiles.index[0]: "low_vol_stable",
        }
        if len(state_profiles) > 1:
            regime_names[state_profiles.index[1]] = "moderate_transition"
        if len(state_profiles) > 2:
            regime_names[state_profiles.index[2]] = "high_vol_crisis"

        print(f"  Regimes: {regime_names}")

        return best_model, regime_names

    def _detect_change_points(self, series):
        """Detect structural breaks using PELT algorithm."""
        algo = rpt.Pelt(model="rbf", min_size=10).fit(series.reshape(-1, 1))
        change_points = algo.predict(pen=3)
        return change_points

def main():
    trainer = RegimeModelTrainer()
    trainer.run()

if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
import statsmodels.api as sm

class VolatilityRegressorTrainer:
    """Train volatility regression models."""

    FEATURE_COLS = [
        "volatility_7d", "volatility_30d", "rsi_14", "atr_14",
        "bb_width", "volume_sma_ratio", "drawdown", "price_sma50_ratio", "macd_hist"
    ]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent.parent / "data" / "processed"
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent.parent / "models"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Train volatility regression models."""
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")

        # Compute target: forward 7-day volatility
        df["target_volatility"] = df["volatility_7d"].shift(-7)
        df = df.dropna(subset=["target_volatility"])

        X = df[self.FEATURE_COLS].fillna(0)
        y = df["target_volatility"]

        # Train linear regression
        print("\nTraining Linear Regression...")
        linreg = self._train_linear_regression(X, y)
        joblib.dump(linreg, self.artifacts_dir / "volatility_linreg.joblib")
        print("Saved volatility_linreg.joblib")

        # Train quantile regression at 10%, 50%, 90%
        for q in [0.1, 0.5, 0.9]:
            print(f"\nTraining Quantile Regression (q={q})...")
            qreg = self._train_quantile_regression(X, y, q)
            joblib.dump(qreg, self.artifacts_dir / f"volatility_qreg_{int(q*100)}.joblib")
            print(f"Saved volatility_qreg_{int(q*100)}.joblib")

        # Save feature list
        joblib.dump(self.FEATURE_COLS, self.artifacts_dir / "regression_features.joblib")
        print("\nRegression training complete.")

    def _train_linear_regression(self, X, y):
        """Train and evaluate linear regression."""
        tscv = TimeSeriesSplit(n_splits=5)

        mae_scores = []
        r2_scores = []

        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            model = LinearRegression()
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            mae_scores.append(mean_absolute_error(y_test, y_pred))
            r2_scores.append(r2_score(y_test, y_pred))

        print(f"  CV MAE: {np.mean(mae_scores):.6f}")
        print(f"  CV R²: {np.mean(r2_scores):.4f}")

        # Train on full data
        model = LinearRegression()
        model.fit(X, y)
        return model

    def _train_quantile_regression(self, X, y, quantile):
        """Train quantile regression model."""
        # Add constant for statsmodels
        X_const = sm.add_constant(X)

        model = sm.QuantReg(y, X_const)
        result = model.fit(q=quantile)

        print(f"  Converged: {result.mse_resid:.6f} MSE")

        return result

def main():
    trainer = VolatilityRegressorTrainer()
    trainer.run()

if __name__ == "__main__":
    main()

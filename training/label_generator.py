import pandas as pd
import numpy as np
from pathlib import Path

class LabelGenerator:
    """Generate risk labels from composite risk score."""

    def __init__(self, processed_dir: Path = None):
        self.processed_dir = processed_dir or Path(__file__).parent / "data" / "processed"

    def run(self) -> None:
        """Generate and add risk labels to features."""
        print("Generating risk labels...")

        features_path = self.processed_dir / "features.csv"
        df = pd.read_csv(features_path)

        df["risk_label"] = self._compute_labels(df)

        output_path = self.processed_dir / "features_with_labels.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved labeled features to {output_path}")
        print(f"Label distribution: {df['risk_label'].value_counts().sort_index().to_dict()}")

    def _compute_labels(self, df: pd.DataFrame) -> pd.Series:
        """Compute risk labels using absolute financial thresholds."""
        # FIX #3: Replace relative percentile-based labeling with absolute conditions
        # This prevents severe drawdowns from being labeled "low risk" due to relative ranking

        drawdown = df["drawdown"].abs()
        volatility_30d = df["volatility_30d"]

        labels = np.zeros(len(df), dtype=int)  # Default to low risk (0)

        # High Risk: drawdown < -30% OR volatility > 2%
        high_risk_mask = (drawdown > 30.0) | (volatility_30d > 0.02)
        labels[high_risk_mask] = 2

        # Medium Risk: drawdown between -15% and -30% OR volatility between 1% and 2%
        # Only apply if not already high risk
        medium_risk_mask = (
            ((drawdown >= 15.0) & (drawdown <= 30.0)) |
            ((volatility_30d >= 0.01) & (volatility_30d <= 0.02))
        ) & (~high_risk_mask)
        labels[medium_risk_mask] = 1

        # Low Risk: everything else (default)

        return pd.Series(labels, index=df.index)

    def _min_max_normalize(self, series: pd.Series) -> pd.Series:
        """FIX #4: Min-max normalize with outlier clipping at 5th-95th percentiles."""
        # Clip to 5th and 95th percentiles to prevent single outliers from compressing variance
        percentile_5 = series.quantile(0.05)
        percentile_95 = series.quantile(0.95)

        clipped_series = series.clip(lower=percentile_5, upper=percentile_95)

        min_val = clipped_series.min()
        max_val = clipped_series.max()
        if max_val == min_val:
            return pd.Series(0, index=series.index)
        return (clipped_series - min_val) / (max_val - min_val)

def main():
    generator = LabelGenerator()
    generator.run()

if __name__ == "__main__":
    main()

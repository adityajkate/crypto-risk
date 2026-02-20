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
        """Compute composite risk score and assign labels."""
        # Normalize features to [0, 1]
        norm_vol = self._min_max_normalize(df["volatility_30d"])
        norm_dd = self._min_max_normalize(df["drawdown"].abs())

        volume_spike = np.maximum(0, df["volume_sma_ratio"] - 1)
        norm_vs = self._min_max_normalize(volume_spike)

        # Composite score
        composite = 0.5 * norm_vol + 0.3 * norm_dd + 0.2 * norm_vs

        # Assign labels using quantiles (equal frequency)
        labels = pd.qcut(composite, q=3, labels=[0, 1, 2])
        return labels.astype(int)

    def _min_max_normalize(self, series: pd.Series) -> pd.Series:
        """Min-max normalize to [0, 1]."""
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(0, index=series.index)
        return (series - min_val) / (max_val - min_val)

def main():
    generator = LabelGenerator()
    generator.run()

if __name__ == "__main__":
    main()

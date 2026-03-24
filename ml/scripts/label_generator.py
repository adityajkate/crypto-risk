import pandas as pd
import numpy as np
from pathlib import Path


class LabelGenerator:
    """Generate forward-looking risk labels based on future adverse events."""

    def __init__(self, processed_dir: Path = None):
        self.processed_dir = (
            processed_dir or Path(__file__).parent.parent / "data" / "processed"
        )

    def run(self) -> None:
        """Generate and add risk labels to features."""
        print("Generating forward-looking risk labels...")

        features_path = self.processed_dir / "features.csv"
        df = pd.read_csv(features_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(["coin_id", "timestamp"]).reset_index(drop=True)

        df["risk_label"] = self._compute_forward_labels(df)

        # Drop rows where we can't compute future labels (last 7 days per coin)
        df = df.dropna(subset=["risk_label"])
        df["risk_label"] = df["risk_label"].astype(int)

        output_path = self.processed_dir / "features_with_labels.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved labeled features to {output_path}")
        print(
            f"Label distribution: {df['risk_label'].value_counts().sort_index().to_dict()}"
        )
        print(
            f"Class percentages: {(df['risk_label'].value_counts(normalize=True) * 100).round(2).to_dict()}"
        )
        print(f"Total samples: {len(df)}")

    def _compute_forward_labels(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute risk labels based on FUTURE VOLATILITY (next 3 days).

        KEY CHANGES:
        1. Wider percentile gaps (35th-75th) for clearer class boundaries
        2. More extreme thresholds to reduce Medium class ambiguity
        3. Focus on separability over balance

        Risk levels:
        - 0 (Low): Future volatility below coin's 35th percentile
        - 1 (Medium): Future volatility between 35th-75th percentile
        - 2 (High): Future volatility above 75th percentile OR severe drawdown
        """
        print("\nGenerating volatility-based risk labels (3-day window, wider gaps)...")

        # Add log_returns if not present
        if "log_returns" not in df.columns:
            df["log_returns"] = np.log(
                df["close"] / df.groupby("coin_id")["close"].shift(1)
            )

        # Compute future volatility (vectorized)
        df["future_vol"] = df.groupby("coin_id")["log_returns"].transform(
            lambda x: x.shift(-1).rolling(3, min_periods=3).std()
        )

        # Compute future max drawdown (vectorized)
        df["future_drawdown"] = df.groupby("coin_id")["close"].transform(
            lambda x: ((x.shift(-1).rolling(3, min_periods=3).min() - x) / x) * 100
        )

        labels = []

        for coin_id in df["coin_id"].unique():
            coin_df = df[df["coin_id"] == coin_id].copy().reset_index(drop=True)
            coin_labels = np.full(len(coin_df), np.nan)

            # Pre-compute 3-day rolling volatility for entire history
            coin_df["rolling_vol_3d"] = (
                coin_df["log_returns"].rolling(3, min_periods=3).std()
            )

            # Pre-compute 3-day rolling drawdown for entire history
            rolling_dd = []
            for i in range(len(coin_df)):
                if i < 3:
                    rolling_dd.append(np.nan)
                else:
                    window_prices = coin_df.iloc[i - 3 : i]["close"].values
                    ref_price = coin_df.iloc[i - 3]["close"]
                    dd = ((window_prices.min() - ref_price) / ref_price) * 100
                    rolling_dd.append(dd)
            coin_df["rolling_dd_3d"] = rolling_dd

            for i in range(len(coin_df)):
                # Need at least 30 past days for percentiles + 3 future days
                if i < 30 or pd.isna(coin_df.iloc[i]["future_vol"]):
                    continue

                future_vol = coin_df.iloc[i]["future_vol"]
                future_drawdown = coin_df.iloc[i]["future_drawdown"]

                # Use expanding percentiles (only past data)
                past_vols = coin_df.iloc[:i]["rolling_vol_3d"].dropna()
                past_dds = coin_df.iloc[:i]["rolling_dd_3d"].dropna()

                if len(past_vols) < 30 or len(past_dds) < 30:
                    continue

                # Adjusted percentiles for MORE SEPARABLE classes
                # Target: ~35% low, ~35% medium, ~30% high
                # Wider gaps between thresholds for clearer boundaries
                p35 = np.percentile(past_vols, 35)
                p75 = np.percentile(past_vols, 75)
                p15_drawdown = np.percentile(past_dds, 15)

                # Assign label with clearer separation
                if future_vol >= p75 or future_drawdown <= p15_drawdown:
                    coin_labels[i] = 2  # High risk: top 25% vol or severe drawdown
                elif future_vol >= p35:
                    coin_labels[i] = 1  # Medium risk: 35th-75th percentile
                else:
                    coin_labels[i] = 0  # Low risk: bottom 35%

            labels.extend(coin_labels)

        return pd.Series(labels, index=df.index)

    def _min_max_normalize(self, series: pd.Series) -> pd.Series:
        """Min-max normalize with outlier clipping at 5th-95th percentiles."""
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

import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.feature_engine import MarketFeatureEngine


class Preprocessor:
    def __init__(self, raw_dir: Path = None, processed_dir: Path = None):
        self.raw_dir = raw_dir or Path(__file__).parent.parent / "data" / "raw"
        self.processed_dir = (
            processed_dir or Path(__file__).parent.parent / "data" / "processed"
        )
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.feature_engine = MarketFeatureEngine()

    def run(self) -> None:
        """Process all raw data files and save features."""
        print("Starting preprocessing...")

        all_features = []
        raw_files = list(self.raw_dir.glob("*_history.csv"))

        for file_path in raw_files:
            coin_id = file_path.stem.replace("_history", "")
            print(f"Processing {coin_id}...")

            df = self._load_and_convert(file_path, coin_id)
            if df is not None and len(df) > 50:
                features = self.feature_engine.transform(df)
                features["coin_id"] = coin_id
                all_features.append(features)

        if all_features:
            combined = pd.concat(all_features, ignore_index=True)
            output_path = self.processed_dir / "features.csv"
            combined.to_csv(output_path, index=False)
            print(f"Saved features to {output_path} ({len(combined)} rows)")
        else:
            print("No features generated.")

    def _load_and_convert(self, file_path: Path, coin_id: str) -> pd.DataFrame:
        """Load raw data - now expects real OHLCV format."""
        try:
            df = pd.read_csv(file_path)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Check if we have real OHLC data
            if all(col in df.columns for col in ["open", "high", "low", "close", "volume"]):
                # Real OHLC data - use as is
                return df[["timestamp", "open", "high", "low", "close", "volume"]]
            elif "price" in df.columns:
                # Old format with single price - create approximate OHLC
                print(f"  Warning: {coin_id} has single price data, creating approximate OHLC")
                df["open"] = df["price"].shift(1).fillna(df["price"])
                df["high"] = df["price"] * 1.01
                df["low"] = df["price"] * 0.99
                df["close"] = df["price"]
                df["volume"] = df.get("volume", 0)
                return df[["timestamp", "open", "high", "low", "close", "volume"]]
            else:
                print(f"  Error: {coin_id} has unknown format")
                return None

        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None



def main():
    preprocessor = Preprocessor()
    preprocessor.run()


if __name__ == "__main__":
    main()

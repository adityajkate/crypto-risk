import asyncio
import pandas as pd
from pathlib import Path
from typing import List
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.coingecko_client import CoinGeckoClient

class TrainingDataCollector:
    def __init__(self, output_dir: Path = None, coin_limit: int = 10):
        self.output_dir = output_dir or Path(__file__).parent / "data" / "raw"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.coin_limit = coin_limit
        self.client = CoinGeckoClient()

    async def collect(self) -> None:
        """Fetch and save data for top N coins."""
        print(f"Fetching top {self.coin_limit} coins...")
        coins = await self.client.fetch_top_coins(self.coin_limit)

        for i, coin in enumerate(coins, 1):
            print(f"[{i}/{len(coins)}] Fetching {coin['name']} ({coin['id']})...")
            try:
                df = await self.client.fetch_coin_history(coin['id'])
                self._save_raw_data(coin['id'], df)
            except Exception as e:
                print(f"Error fetching {coin['id']}: {e}")

        await self.client.close()
        print("Data collection complete.")

    def _save_raw_data(self, coin_id: str, df: pd.DataFrame) -> None:
        """Save raw data to CSV."""
        df.to_csv(self.output_dir / f"{coin_id}_history.csv", index=False)

async def main():
    collector = TrainingDataCollector()
    await collector.collect()

if __name__ == "__main__":
    asyncio.run(main())

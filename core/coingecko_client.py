import asyncio
import httpx
import pandas as pd
from typing import List, Dict, Any, Optional
import os

class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"
    RATE_LIMIT_DELAY = 20.0  # 3 requests per minute (very conservative)

    def __init__(self, api_key: Optional[str] = None):
        # Use API key from environment
        self.api_key = api_key or os.getenv("COINGECKO_API_KEY")

        headers = {}
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key

        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)
        self._last_request_time = 0

    async def _rate_limited_request(self, endpoint: str, params: dict = None, max_retries: int = 5) -> dict:
        """Make rate-limited request to CoinGecko API with exponential backoff."""
        import time

        for attempt in range(max_retries):
            try:
                elapsed = time.time() - self._last_request_time
                if elapsed < self.RATE_LIMIT_DELAY:
                    await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)

                url = f"{self.BASE_URL}/{endpoint}"
                response = await self.client.get(url, params=params)
                self._last_request_time = time.time()

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit error
                    if attempt < max_retries - 1:
                        # Exponential backoff: 20, 40, 80, 160 seconds
                        backoff_time = 20 * (2 ** attempt)
                        print(f"  Rate limit hit, waiting {backoff_time}s before retry {attempt + 2}/{max_retries}...")
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        print(f"  Max retries exceeded for rate limit, skipping...")
                        return {}  # Return empty dict instead of raising
                else:
                    raise  # Re-raise if not 429

    async def fetch_top_coins(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch top coins by market cap."""
        data = await self._rate_limited_request(
            "coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1
            }
        )
        return [{"id": c["id"], "symbol": c["symbol"], "name": c["name"]} for c in data]

    async def fetch_coin_history(self, coin_id: str, days: str = "365") -> pd.DataFrame:
        """Fetch OHLCV history for a coin using real OHLC endpoint."""
        # Fetch OHLC data (open, high, low, close)
        ohlc_data = await self._rate_limited_request(
            f"coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": days}
        )

        # Fetch volume data separately
        market_data = await self._rate_limited_request(
            f"coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days}
        )

        # OHLC format: [timestamp, open, high, low, close]
        if not ohlc_data:
            print(f"  Warning: No OHLC data for {coin_id}")
            return pd.DataFrame()

        df = pd.DataFrame(ohlc_data, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        # Add volume from market_chart
        volumes = market_data.get("total_volumes", [])
        if volumes:
            volume_df = pd.DataFrame(volumes, columns=["vol_timestamp", "volume"])
            volume_df["vol_timestamp"] = pd.to_datetime(volume_df["vol_timestamp"], unit="ms")

            # Round to daily and merge
            df["date"] = df["timestamp"].dt.floor("D")
            volume_df["date"] = volume_df["vol_timestamp"].dt.floor("D")
            volume_df = volume_df.groupby("date")["volume"].mean().reset_index()

            df = df.merge(volume_df, on="date", how="left")
            df = df.drop(columns=["date"])
            df["volume"] = df["volume"].fillna(0)
        else:
            df["volume"] = 0

        return df

    async def close(self):
        await self.client.aclose()

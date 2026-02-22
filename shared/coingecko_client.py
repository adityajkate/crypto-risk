import asyncio
import httpx
import pandas as pd
from typing import List, Dict, Any, Optional
import os

class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"
    RATE_LIMIT_DELAY = 12.0  # Very conservative: 5 req/min for Demo API

    def __init__(self, api_key: Optional[str] = None):
        # Use API key from environment if not provided
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
                        # Exponential backoff: 10, 20, 40, 80 seconds
                        backoff_time = 10 * (2 ** attempt)
                        print(f"  Rate limit hit, waiting {backoff_time}s before retry {attempt + 2}/{max_retries}...")
                        await asyncio.sleep(backoff_time)
                        continue
                raise  # Re-raise if not 429 or max retries exceeded

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
        """Fetch OHLCV history for a coin. Uses 365 days (free tier limit)."""
        # CoinGecko free tier only allows up to 365 days without auth
        data = await self._rate_limited_request(
            f"coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days}
        )

        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        market_caps = data.get("market_caps", [])

        df = pd.DataFrame({
            "timestamp": [p[0] for p in prices],
            "price": [p[1] for p in prices],
            "volume": [v[1] for v in volumes] if volumes else [0] * len(prices),
            "market_cap": [m[1] for m in market_caps] if market_caps else [0] * len(prices)
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    async def close(self):
        await self.client.aclose()

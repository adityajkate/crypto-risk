"""Real-time data client for CoinGecko API with authentication."""
import asyncio
import httpx
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime


class CoinGeckoRealtimeClient:
    """CoinGecko API client with API key support for real-time data."""

    BASE_URL = "https://api.coingecko.com/api/v3"
    PRO_BASE_URL = "https://pro-api.coingecko.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, rate_limit_delay: float = 1.0):
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0

        # Check if it's a Demo key (starts with CG-) or Pro key
        # Demo keys use regular API endpoint with x-cg-demo-api-key header
        is_demo_key = api_key and api_key.startswith("CG-")

        if is_demo_key:
            self.base_url = self.BASE_URL
            headers = {"x-cg-demo-api-key": api_key}
        elif api_key:
            self.base_url = self.PRO_BASE_URL
            headers = {"x-cg-pro-api-key": api_key}
        else:
            self.base_url = self.BASE_URL
            headers = {}

        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)

    async def _rate_limited_request(self, endpoint: str, params: dict = None) -> dict:
        """Make rate-limited request to CoinGecko API - NO RETRIES, fail fast."""
        import time

        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

        url = f"{self.base_url}/{endpoint}"
        response = await self.client.get(url, params=params)
        self._last_request_time = time.time()

        response.raise_for_status()
        return response.json()

    async def get_coin_price(self, coin_id: str) -> Dict[str, Any]:
        """Get current price and market data for a coin."""
        data = await self._rate_limited_request(
            f"coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false"
            }
        )

        market_data = data.get("market_data", {})
        return {
            "id": data.get("id"),
            "symbol": data.get("symbol"),
            "name": data.get("name"),
            "image": data.get("image", {}).get("large")
            or data.get("image", {}).get("small")
            or data.get("image", {}).get("thumb"),
            "current_price": market_data.get("current_price", {}).get("usd"),
            "market_cap": market_data.get("market_cap", {}).get("usd"),
            "total_volume": market_data.get("total_volume", {}).get("usd"),
            "price_change_24h": market_data.get("price_change_24h"),
            "price_change_percentage_24h": market_data.get("price_change_percentage_24h"),
            "market_cap_rank": market_data.get("market_cap_rank"),
            "circulating_supply": market_data.get("circulating_supply"),
            "total_supply": market_data.get("total_supply"),
            "ath": market_data.get("ath", {}).get("usd"),
            "atl": market_data.get("atl", {}).get("usd"),
            "last_updated": data.get("last_updated")
        }

    async def get_coin_ohlc(self, coin_id: str, days: int = 7) -> pd.DataFrame:
        """Get OHLC data for a coin."""
        data = await self._rate_limited_request(
            f"coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": days}
        )

        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    async def get_trending_coins(self) -> List[Dict[str, Any]]:
        """Get trending coins."""
        data = await self._rate_limited_request("search/trending")

        trending = []
        for item in data.get("coins", [])[:10]:
            coin = item.get("item", {})
            trending.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "price_btc": coin.get("price_btc")
            })
        return trending

    async def get_global_market_data(self) -> Dict[str, Any]:
        """Get global cryptocurrency market data."""
        data = await self._rate_limited_request("global")

        global_data = data.get("data", {})
        return {
            "total_market_cap": global_data.get("total_market_cap", {}).get("usd"),
            "total_volume": global_data.get("total_volume", {}).get("usd"),
            "market_cap_change_percentage_24h": global_data.get("market_cap_change_percentage_24h_usd"),
            "active_cryptocurrencies": global_data.get("active_cryptocurrencies")
        }

    async def search_coins(self, query: str) -> Dict[str, Any]:
        """Search for coins by name or symbol."""
        return await self._rate_limited_request("search", params={"query": query})

    async def get_multiple_coins_data(self, coin_ids: List[str]) -> List[Dict[str, Any]]:
        """Get data for multiple coins at once."""
        data = await self._rate_limited_request(
            "coins/markets",
            params={
                "vs_currency": "usd",
                "ids": ",".join(coin_ids),
                "order": "market_cap_desc",
                "sparkline": "false"
            }
        )

        return [{
            "id": coin.get("id"),
            "symbol": coin.get("symbol"),
            "name": coin.get("name"),
            "current_price": coin.get("current_price"),
            "market_cap": coin.get("market_cap"),
            "total_volume": coin.get("total_volume"),
            "price_change_24h": coin.get("price_change_24h"),
            "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
            "market_cap_rank": coin.get("market_cap_rank")
        } for coin in data]

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

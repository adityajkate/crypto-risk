"""Real-time news and sentiment client for CryptoPanic API."""
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime


class CryptoPanicClient:
    """CryptoPanic API client for crypto news and sentiment."""

    BASE_URL = "https://cryptopanic.com/api/v1"

    def __init__(self, api_key: str, rate_limit_delay: float = 1.0):
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _rate_limited_request(self, endpoint: str, params: dict = None) -> dict:
        """Make rate-limited request to CryptoPanic API."""
        import time
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

        if params is None:
            params = {}
        params["auth_token"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"
        response = await self.client.get(url, params=params)
        self._last_request_time = time.time()

        response.raise_for_status()
        return response.json()

    async def get_posts(
        self,
        currencies: Optional[str] = None,
        kind: str = "news",
        filter_type: str = "hot",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get news posts from CryptoPanic.

        Args:
            currencies: Comma-separated coin symbols (e.g., "BTC,ETH")
            kind: Type of posts - "news" or "media" or "all"
            filter_type: Filter - "rising", "hot", "bullish", "bearish", "important", "saved", "lol"
            limit: Number of posts to return (max 100)
        """
        params = {
            "kind": kind,
            "filter": filter_type
        }

        if currencies:
            params["currencies"] = currencies

        data = await self._rate_limited_request("posts", params=params)

        posts = []
        for post in data.get("results", [])[:limit]:
            posts.append({
                "id": post.get("id"),
                "title": post.get("title"),
                "url": post.get("url"),
                "source": post.get("source", {}).get("title"),
                "published_at": post.get("published_at"),
                "created_at": post.get("created_at"),
                "kind": post.get("kind"),
                "currencies": [c.get("code") for c in post.get("currencies", [])],
                "votes": {
                    "positive": post.get("votes", {}).get("positive", 0),
                    "negative": post.get("votes", {}).get("negative", 0),
                    "important": post.get("votes", {}).get("important", 0),
                    "liked": post.get("votes", {}).get("liked", 0),
                    "disliked": post.get("votes", {}).get("disliked", 0),
                    "lol": post.get("votes", {}).get("lol", 0),
                    "toxic": post.get("votes", {}).get("toxic", 0),
                    "saved": post.get("votes", {}).get("saved", 0)
                }
            })

        return posts

    async def get_sentiment_for_coin(self, currency: str) -> Dict[str, Any]:
        """
        Get aggregated sentiment for a specific coin.

        Args:
            currency: Coin symbol (e.g., "BTC", "ETH")
        """
        # Get recent posts for the coin
        bullish_posts = await self.get_posts(currencies=currency, filter_type="bullish", limit=50)
        bearish_posts = await self.get_posts(currencies=currency, filter_type="bearish", limit=50)
        important_posts = await self.get_posts(currencies=currency, filter_type="important", limit=50)

        # Calculate sentiment scores
        total_bullish = sum(p["votes"]["positive"] for p in bullish_posts)
        total_bearish = sum(p["votes"]["negative"] for p in bearish_posts)
        total_important = sum(p["votes"]["important"] for p in important_posts)

        total_votes = total_bullish + total_bearish
        sentiment_score = (total_bullish - total_bearish) / max(total_votes, 1)

        return {
            "currency": currency,
            "sentiment_score": sentiment_score,  # Range: -1 (bearish) to 1 (bullish)
            "bullish_count": len(bullish_posts),
            "bearish_count": len(bearish_posts),
            "important_count": len(important_posts),
            "total_positive_votes": total_bullish,
            "total_negative_votes": total_bearish,
            "total_important_votes": total_important,
            "recent_posts": (bullish_posts + bearish_posts)[:10]
        }

    async def get_trending_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending/hot news across all cryptocurrencies."""
        return await self.get_posts(filter_type="hot", limit=limit)

    async def get_important_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get important news marked by the community."""
        return await self.get_posts(filter_type="important", limit=limit)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

"""Google Trends client for search interest tracking."""
import asyncio
from pytrends.request import TrendReq
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class GoogleTrendsClient:
    """Client for Google Trends search interest data."""

    def __init__(self):
        self.pytrends = None
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour cache

    def _init_pytrends(self):
        """Initialize pytrends (lazy loading)."""
        if not self.pytrends:
            self.pytrends = TrendReq(hl='en-US', tz=0)

    def _get_cache_key(self, keyword: str) -> str:
        """Generate cache key for keyword."""
        return f"trends_{keyword.lower()}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid."""
        if cache_key not in self._cache:
            return False

        cache_entry = self._cache[cache_key]
        age = (datetime.utcnow() - cache_entry["timestamp"]).total_seconds()
        return age < self._cache_ttl

    async def get_search_interest(self, keyword: str, timeframe: str = "now 7-d") -> Dict[str, Any]:
        """
        Get Google Trends search interest for a keyword.

        Args:
            keyword: Search term (e.g., "bitcoin", "ethereum")
            timeframe: Time range (e.g., "now 7-d", "today 1-m")

        Returns:
            {
                "current_interest": float (0-100),
                "normalized": float (0-1),
                "trend": str ("rising", "falling", "stable"),
                "change_7d": float
            }
        """
        try:
            cache_key = self._get_cache_key(keyword)

            # Check cache
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]["data"]

            # Fetch from Google Trends (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_trends,
                keyword,
                timeframe
            )

            # Cache result
            self._cache[cache_key] = {
                "data": result,
                "timestamp": datetime.utcnow()
            }

            return result

        except Exception as e:
            logger.error(f"Error fetching Google Trends for {keyword}: {e}")
            # Return neutral on error
            return {
                "current_interest": 50.0,
                "normalized": 0.5,
                "trend": "stable",
                "change_7d": 0.0
            }

    def _fetch_trends(self, keyword: str, timeframe: str) -> Dict[str, Any]:
        """Fetch trends data (blocking call)."""
        self._init_pytrends()

        # Build payload
        self.pytrends.build_payload(
            kw_list=[keyword],
            timeframe=timeframe,
            geo='',  # Worldwide
            gprop=''
        )

        # Get interest over time
        interest_df = self.pytrends.interest_over_time()

        if interest_df.empty or keyword not in interest_df.columns:
            return {
                "current_interest": 50.0,
                "normalized": 0.5,
                "trend": "stable",
                "change_7d": 0.0
            }

        # Get current and historical values
        values = interest_df[keyword].values
        current = float(values[-1])
        first = float(values[0])

        # Calculate change
        change_7d = current - first

        # Determine trend
        if change_7d > 10:
            trend = "rising"
        elif change_7d < -10:
            trend = "falling"
        else:
            trend = "stable"

        # Normalize to 0-1 scale
        normalized = current / 100.0

        return {
            "current_interest": current,
            "normalized": normalized,
            "trend": trend,
            "change_7d": change_7d
        }

    async def get_batch_interest(self, keywords: list) -> Dict[str, Dict[str, Any]]:
        """
        Get search interest for multiple keywords.

        Args:
            keywords: List of search terms

        Returns:
            Dict mapping keyword to interest data
        """
        results = {}

        for keyword in keywords:
            results[keyword] = await self.get_search_interest(keyword)
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        return results

    async def get_related_queries(self, keyword: str) -> Dict[str, Any]:
        """
        Get related queries for a keyword (rising and top).

        Args:
            keyword: Search term

        Returns:
            {
                "rising": list,
                "top": list
            }
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._fetch_related_queries,
                keyword
            )
            return result

        except Exception as e:
            logger.error(f"Error fetching related queries for {keyword}: {e}")
            return {"rising": [], "top": []}

    def _fetch_related_queries(self, keyword: str) -> Dict[str, Any]:
        """Fetch related queries (blocking call)."""
        self._init_pytrends()

        self.pytrends.build_payload(
            kw_list=[keyword],
            timeframe="now 7-d",
            geo='',
            gprop=''
        )

        related = self.pytrends.related_queries()

        if not related or keyword not in related:
            return {"rising": [], "top": []}

        rising = []
        top = []

        if related[keyword]["rising"] is not None:
            rising = related[keyword]["rising"]["query"].tolist()[:5]

        if related[keyword]["top"] is not None:
            top = related[keyword]["top"]["query"].tolist()[:5]

        return {
            "rising": rising,
            "top": top
        }

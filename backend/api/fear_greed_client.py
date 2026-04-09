"""Fear & Greed Index client for alternative.me API."""

import asyncio
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FearGreedClient:
    """Client for Crypto Fear & Greed Index API."""

    BASE_URL = "https://api.alternative.me/fng/"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self._cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache

    async def get_current_index(self) -> Dict[str, Any]:
        """
        Get current Fear & Greed Index.

        Returns:
            {
                "value": int (0-100),
                "value_classification": str ("Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"),
                "timestamp": str,
                "normalized": float (-1 to 1)
            }
        """
        try:
            # Check cache
            if self._cache and self._cache_timestamp:
                age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
                if age < self._cache_ttl:
                    return self._cache

            # Fetch from API
            response = await self.client.get(f"{self.BASE_URL}?limit=1")
            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                raise ValueError("No data in Fear & Greed API response")

            fng_data = data["data"][0]
            value = int(fng_data["value"])
            classification = fng_data["value_classification"]

            # Normalize to -1 (Extreme Fear) to 1 (Extreme Greed)
            # 0-100 scale → -1 to 1 scale
            normalized = (value - 50) / 50.0

            result = {
                "value": value,
                "value_classification": classification,
                "timestamp": fng_data["timestamp"],
                "normalized": normalized,
            }

            # Update cache
            self._cache = result
            self._cache_timestamp = datetime.utcnow()

            return result

        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            # Return neutral on error
            return {
                "value": 50,
                "value_classification": "Neutral",
                "timestamp": str(int(datetime.utcnow().timestamp())),
                "normalized": 0.0,
            }

    async def get_historical(self, limit: int = 7) -> list:
        """
        Get historical Fear & Greed Index data.

        Args:
            limit: Number of days to fetch (max 30)

        Returns:
            List of daily index values
        """
        try:
            response = await self.client.get(f"{self.BASE_URL}?limit={limit}")
            response.raise_for_status()
            data = response.json()

            historical = []
            for item in data.get("data", []):
                value = int(item["value"])
                normalized = (value - 50) / 50.0

                historical.append(
                    {
                        "value": value,
                        "value_classification": item["value_classification"],
                        "timestamp": item["timestamp"],
                        "normalized": normalized,
                    }
                )

            return historical

        except Exception as e:
            logger.error(f"Error fetching historical Fear & Greed: {e}")
            return []

    async def get_trend(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze Fear & Greed trend over recent days.

        Returns:
            {
                "current": float,
                "average": float,
                "trend": str ("increasing", "decreasing", "stable"),
                "change": float
            }
        """
        try:
            historical = await self.get_historical(limit=days)

            if not historical:
                return {
                    "current": 0.0,
                    "average": 0.0,
                    "trend": "stable",
                    "change": 0.0,
                }

            values = [item["normalized"] for item in historical]
            current = values[0]
            average = sum(values) / len(values)
            change = current - values[-1] if len(values) > 1 else 0.0

            # Determine trend
            if change > 0.1:
                trend = "increasing"
            elif change < -0.1:
                trend = "decreasing"
            else:
                trend = "stable"

            return {
                "current": current,
                "average": average,
                "trend": trend,
                "change": change,
            }

        except Exception as e:
            logger.error(f"Error analyzing Fear & Greed trend: {e}")
            return {"current": 0.0, "average": 0.0, "trend": "stable", "change": 0.0}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

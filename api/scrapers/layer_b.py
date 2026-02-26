"""Layer B Scraper - Early signal sources (Twitter/X, Reddit, Telegram)."""
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)


class LayerBScraper:
    """Scraper for early signal sources (social media, forums)."""

    def __init__(self, scrape_queue: asyncio.Queue = None):
        self.scrape_queue = scrape_queue  # Keep for compatibility, but will use event_store
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.running = False

    async def scrape_reddit(self, coin: str, subreddit: str = "CryptoCurrency") -> List[Dict[str, Any]]:
        """
        Scrape Reddit posts mentioning the coin.
        Uses Reddit JSON API (no auth required for public posts).
        """
        try:
            url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100"
            headers = {"User-Agent": "CryptoRiskLens/1.0"}

            response = await self.client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            posts = []

            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                text = f"{title}. {selftext}"

                # Check if post mentions the coin
                if coin.lower() in text.lower():
                    # Try to get image from Reddit post
                    image_url = None
                    if post_data.get("thumbnail") and post_data.get("thumbnail").startswith("http"):
                        image_url = post_data.get("thumbnail")
                    elif post_data.get("url") and any(post_data.get("url", "").endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        image_url = post_data.get("url")
                    elif post_data.get("preview"):
                        try:
                            image_url = post_data["preview"]["images"][0]["source"]["url"]
                        except (KeyError, IndexError):
                            pass

                    posts.append({
                        "coin": coin,
                        "title": title,
                        "summary": selftext[:200] if selftext else title,
                        "text": text[:1000],
                        "full_content": selftext if selftext else title,
                        "image_url": image_url,
                        "source_type": "layer_b",
                        "source": f"reddit_{subreddit}",
                        "platform_id": "reddit",
                        "timestamp": datetime.utcnow(),
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "engagement_count": post_data.get("score", 0) + post_data.get("num_comments", 0),
                        "credibility_weight": 0.4  # Layer B weight
                    })

            return posts

        except Exception as e:
            logger.error(f"Error scraping Reddit: {e}")
            return []

    async def scrape_twitter_nitter(self, coin: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape Twitter/X via Nitter instances (public Twitter mirror).
        Note: This is a fallback method. For production, use Twitter API.
        """
        try:
            # Use public Nitter instance
            nitter_instance = "https://nitter.net"
            tweets = []

            for keyword in keywords[:3]:  # Limit keywords
                url = f"{nitter_instance}/search?f=tweets&q={keyword}+{coin}"

                try:
                    response = await self.client.get(url, timeout=15.0)
                    if response.status_code == 200:
                        # Basic HTML parsing (in production, use proper parser)
                        text = response.text

                        # Extract tweet content (simplified)
                        tweet_pattern = r'<div class="tweet-content[^"]*">(.*?)</div>'
                        matches = re.findall(tweet_pattern, text, re.DOTALL)

                        for match in matches[:10]:  # Limit per keyword
                            clean_text = re.sub(r'<[^>]+>', '', match).strip()

                            if clean_text and len(clean_text) > 20:
                                tweets.append({
                                    "coin": coin,
                                    "title": clean_text[:100],
                                    "summary": clean_text[:200],
                                    "text": clean_text[:1000],
                                    "full_content": clean_text,
                                    "image_url": None,  # Nitter doesn't provide images easily
                                    "source_type": "layer_b",
                                    "source": "twitter_stream",
                                    "platform_id": "twitter",
                                    "timestamp": datetime.utcnow(),
                                    "url": nitter_instance,
                                    "engagement_count": 0,  # Can't get engagement from Nitter
                                    "credibility_weight": 0.4
                                })

                except Exception as e:
                    logger.warning(f"Error fetching from Nitter for {keyword}: {e}")
                    continue

                await asyncio.sleep(2)  # Rate limiting

            return tweets

        except Exception as e:
            logger.error(f"Error scraping Twitter via Nitter: {e}")
            return []

    async def scrape_bitcointalk(self, coin: str) -> List[Dict[str, Any]]:
        """
        Scrape BitcoinTalk forum posts.
        Uses RSS feed for recent posts.
        """
        try:
            # BitcoinTalk recent posts RSS
            url = "https://bitcointalk.org/index.php?action=.xml;type=rss"

            response = await self.client.get(url)
            response.raise_for_status()

            import feedparser
            feed = feedparser.parse(response.text)
            posts = []

            for entry in feed.entries[:50]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                text = f"{title}. {summary}"

                if coin.lower() in text.lower():
                    posts.append({
                        "coin": coin,
                        "title": title,
                        "summary": summary[:200] if summary else title,
                        "text": text[:1000],
                        "full_content": summary if summary else title,
                        "image_url": None,  # BitcoinTalk RSS doesn't include images
                        "source_type": "layer_b",
                        "source": "bitcointalk_forum",
                        "platform_id": "bitcointalk",
                        "timestamp": datetime.utcnow(),
                        "url": entry.get("link", ""),
                        "engagement_count": 0,
                        "credibility_weight": 0.4
                    })

            return posts

        except Exception as e:
            logger.error(f"Error scraping BitcoinTalk: {e}")
            return []

    async def scrape_all_sources(self, coin: str):
        """Scrape all Layer B sources for a coin."""

        # Define search keywords for the coin
        keywords = [coin, f"${coin[:3].upper()}", f"#{coin}"]

        tasks = [
            self.scrape_reddit(coin, "CryptoCurrency"),
            self.scrape_reddit(coin, coin.lower()),  # Coin-specific subreddit
            self.scrape_twitter_nitter(coin, keywords),
            self.scrape_bitcointalk(coin),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and push to queue
        for result in results:
            if isinstance(result, list):
                for post in result:
                    try:
                        # Import here to get the initialized queue
                        from api.event_store import SCRAPE_QUEUE
                        if SCRAPE_QUEUE:
                            await SCRAPE_QUEUE.put(post)
                        else:
                            logger.warning("SCRAPE_QUEUE not initialized")
                    except asyncio.QueueFull:
                        logger.warning("Scrape queue full, dropping post")

    async def run(self, coins: List[str], interval_minutes: int = 5):
        """
        Run continuous scraping for Layer B sources.

        Args:
            coins: List of coin names to track
            interval_minutes: Polling interval (default: 5 minutes for high frequency)
        """
        self.running = True
        logger.info(f"Layer B scraper started for coins: {coins}")

        while self.running:
            try:
                for coin in coins:
                    await self.scrape_all_sources(coin)
                    await asyncio.sleep(2)  # Small delay between coins

                # Wait for next polling interval
                await asyncio.sleep(interval_minutes * 60)

            except Exception as e:
                logger.error(f"Error in Layer B scraper: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def run_dynamic(self, interval_minutes: int = 5):
        """
        Run continuous scraping with dynamic coin tracking.

        Scrapes coins that are actively being tracked by users.
        """
        self.running = True
        logger.info("Layer B scraper started with dynamic coin tracking")
        print("Layer B scraper started with dynamic coin tracking")  # Console output

        while self.running:
            try:
                # Import here to avoid circular dependency
                from api.event_store import get_active_coins

                active_coins = get_active_coins()

                if active_coins:
                    logger.info(f"Layer B scraping {len(active_coins)} coins: {active_coins}")
                    print(f"Layer B scraping {len(active_coins)} coins: {active_coins}")
                    for coin in active_coins:
                        await self.scrape_all_sources(coin)
                        await asyncio.sleep(2)  # Small delay between coins

                    # Wait for next polling interval after scraping
                    logger.info(f"Layer B: Waiting {interval_minutes} minutes until next scrape")
                    print(f"Layer B: Waiting {interval_minutes} minutes until next scrape")
                    await asyncio.sleep(interval_minutes * 60)
                else:
                    # No coins yet, check again in 30 seconds
                    logger.debug("No active coins to scrape")
                    print("Layer B: No active coins to scrape yet, checking again in 30s")
                    await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in Layer B scraper: {e}")
                print(f"Error in Layer B scraper: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def stop(self):
        """Stop the scraper."""
        self.running = False
        await self.client.aclose()

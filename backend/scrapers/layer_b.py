"""Layer B Scraper - Early signal sources (Twitter, Reddit, Forums)."""
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any
import logging
import praw
import os

logger = logging.getLogger(__name__)


class LayerBScraper:
    """Scraper for early signal sources (social media, forums)."""

    def __init__(self, scrape_queue: asyncio.Queue = None):
        self.scrape_queue = scrape_queue
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=50,
            keepalive_expiry=30.0
        )
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True, limits=limits)
        self.reddit = None
        self.running = False

    def _init_reddit(self):
        """Initialize Reddit client using PRAW."""
        try:
            # Try to initialize PRAW with credentials from environment
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT", "CryptoRiskLens/1.0")

            if client_id and client_secret:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent
                )
                logger.info("Reddit PRAW client initialized")
            else:
                logger.warning("Reddit credentials not found, will use fallback scraping")
                self.reddit = None

        except Exception as e:
            logger.error(f"Error initializing Reddit client: {e}")
            self.reddit = None

    async def scrape_reddit(self, coin: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape Reddit posts mentioning the coin using PRAW.

        Args:
            coin: Primary coin identifier (for storage)
            keywords: List of keywords to match (name, symbol, aliases)
        """
        if keywords is None:
            keywords = [coin]

        posts = []

        try:
            # Initialize Reddit if not done
            if self.reddit is None:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._init_reddit)

            if self.reddit:
                # Use PRAW to scrape
                posts = await self._scrape_reddit_praw(coin, keywords)
            else:
                # Fallback to JSON API
                posts = await self._scrape_reddit_json(coin, keywords)

        except Exception as e:
            logger.error(f"Error scraping Reddit: {e}")

        return posts

    async def _scrape_reddit_praw(self, coin: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Scrape Reddit using PRAW (official API)."""
        posts = []

        try:
            loop = asyncio.get_event_loop()

            # Search in r/CryptoCurrency
            subreddit = await loop.run_in_executor(
                None,
                lambda: self.reddit.subreddit("CryptoCurrency")
            )

            # Get new posts
            new_posts = await loop.run_in_executor(
                None,
                lambda: list(subreddit.new(limit=200))
            )

            for post in new_posts:
                title = post.title
                selftext = post.selftext
                raw_text = f"{title}. {selftext}"
                text = raw_text.lower()

                # Check if post mentions any of the coin keywords
                if any(keyword.lower() in text for keyword in keywords):
                    # Get thumbnail/image
                    image_url = None
                    if hasattr(post, 'thumbnail') and post.thumbnail.startswith("http"):
                        image_url = post.thumbnail
                    elif hasattr(post, 'url') and any(post.url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        image_url = post.url

                    # Get post creation time
                    post_time = datetime.utcnow()
                    if hasattr(post, 'created_utc'):
                        post_time = datetime.fromtimestamp(post.created_utc)

                    posts.append({
                        "coin": coin,
                        "title": title,
                        "summary": selftext[:200] if selftext else title,
                        "text": raw_text[:1000],
                        "full_content": selftext if selftext else title,
                        "image_url": image_url,
                        "source_type": "layer_b",
                        "source": "reddit_cryptocurrency",
                        "platform_id": "reddit",
                        "timestamp": post_time,
                        "url": f"https://reddit.com{post.permalink}",
                        "engagement_count": post.score + post.num_comments,
                        "credibility_weight": 0.4
                    })

        except Exception as e:
            logger.error(f"Error scraping Reddit with PRAW: {e}")

        return posts

    async def _scrape_reddit_json(self, coin: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fallback: Scrape Reddit using JSON API (no auth required)."""
        posts = []

        try:
            url = "https://www.reddit.com/r/CryptoCurrency/new.json?limit=200"
            headers = {"User-Agent": "CryptoRiskLens/1.0"}

            response = await self.client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                raw_text = f"{title}. {selftext}"
                text = raw_text.lower()

                # Check if post mentions any of the coin keywords
                if any(keyword.lower() in text for keyword in keywords):
                    # Try to get image
                    image_url = None
                    if post_data.get("thumbnail") and post_data.get("thumbnail").startswith("http"):
                        image_url = post_data.get("thumbnail")
                    elif post_data.get("url") and any(post_data.get("url", "").endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        image_url = post_data.get("url")

                    # Get post creation time
                    post_time = datetime.utcnow()
                    if post_data.get("created_utc"):
                        post_time = datetime.fromtimestamp(post_data.get("created_utc"))

                    posts.append({
                        "coin": coin,
                        "title": title,
                        "summary": selftext[:200] if selftext else title,
                        "text": raw_text[:1000],
                        "full_content": selftext if selftext else title,
                        "image_url": image_url,
                        "source_type": "layer_b",
                        "source": "reddit_cryptocurrency",
                        "platform_id": "reddit",
                        "timestamp": post_time,
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "engagement_count": post_data.get("score", 0) + post_data.get("num_comments", 0),
                        "credibility_weight": 0.4
                    })

        except Exception as e:
            logger.error(f"Error scraping Reddit JSON: {e}")

        return posts

    async def scrape_google_news(self, coin: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape Google News RSS for crypto mentions.

        Args:
            coin: Primary coin identifier
            keywords: List of keywords to search
        """
        posts = []

        try:
            import feedparser

            # Use first keyword for search
            search_term = keywords[0] if keywords else coin
            url = f"https://news.google.com/rss/search?q={search_term}+cryptocurrency&hl=en-US&gl=US&ceid=US:en"

            response = await self.client.get(url)
            response.raise_for_status()

            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, response.text)

            for entry in feed.entries[:50]:  # Check up to 50 entries
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                raw_text = f"{title}. {summary}"
                text = raw_text.lower()

                # Check if mentions any keyword
                if any(keyword.lower() in text for keyword in keywords):
                    # Parse published date from RSS entry
                    published_date = datetime.utcnow()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        from time import mktime
                        published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        from time import mktime
                        published_date = datetime.fromtimestamp(mktime(entry.updated_parsed))

                    # Google News URLs contain the actual URL in base64 format after 'articles/'
                    article_url = entry.get("link", "")
                    if article_url and "news.google.com" in article_url and "articles/" in article_url:
                        try:
                            import base64
                            import re
                            payload = article_url.split('articles/')[1].split('?')[0]
                            payload += '=' * (-len(payload) % 4)
                            decoded = base64.urlsafe_b64decode(payload)
                            match = re.search(rb'(https?://[^\x00-\x1F\x7F]+)', decoded)
                            if match:
                                article_url = match.group(1).decode('utf-8', errors='ignore')
                        except Exception as e:
                            logger.debug(f"Failed to extract base64 URL for {article_url}: {e}")

                    # Note: Google News RSS only provides short summaries
                    # Full content will be fetched on-demand when user clicks article
                    posts.append({
                        "coin": coin,
                        "title": title,
                        "summary": summary[:500] if summary else title,  # Increased from 200
                        "text": raw_text[:1000],
                        "full_content": summary if summary else title,  # RSS summary only
                        "image_url": None,
                        "source_type": "layer_b",
                        "source": "google_news",
                        "platform_id": "google_news",
                        "timestamp": published_date,
                        "url": article_url,
                        "engagement_count": 0,
                        "credibility_weight": 0.5,  # Between Layer A and B
                        "needs_full_fetch": True  # Mark for on-demand fetching
                    })

        except Exception as e:
            logger.error(f"Error scraping Google News: {e}")

        return posts

    async def scrape_bitcointalk(self, coin: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape BitcoinTalk forum posts.

        Args:
            coin: Primary coin identifier
            keywords: List of keywords to match
        """
        if keywords is None:
            keywords = [coin]

        try:
            url = "https://bitcointalk.org/index.php?action=.xml;type=rss"

            response = await self.client.get(url)
            response.raise_for_status()

            import feedparser
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, response.text)
            posts = []

            for entry in feed.entries[:50]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                raw_text = f"{title}. {summary}"
                text = raw_text.lower()

                if any(keyword.lower() in text for keyword in keywords):
                    # Parse published date from RSS entry
                    published_date = datetime.utcnow()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        from time import mktime
                        published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        from time import mktime
                        published_date = datetime.fromtimestamp(mktime(entry.updated_parsed))

                    posts.append({
                        "coin": coin,
                        "title": title,
                        "summary": summary[:200] if summary else title,
                        "text": raw_text[:1000],
                        "full_content": summary if summary else title,
                        "image_url": None,
                        "source_type": "layer_b",
                        "source": "bitcointalk_forum",
                        "platform_id": "bitcointalk",
                        "timestamp": published_date,
                        "url": entry.get("link", ""),
                        "engagement_count": 0,
                        "credibility_weight": 0.4
                    })

            return posts

        except Exception as e:
            logger.error(f"Error scraping BitcoinTalk: {e}")
            return []

    async def scrape_all_sources(self, coin: str, keywords: List[str] = None):
        """Scrape all Layer B sources for a coin."""
        if keywords is None:
            keywords = [coin]

        # Add hashtag and ticker variants
        social_keywords = keywords + [f"${kw.upper()}" for kw in keywords if len(kw) <= 5]

        tasks = [
            self.scrape_reddit(coin, keywords),
            self.scrape_google_news(coin, social_keywords),
            self.scrape_bitcointalk(coin, keywords),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and push to queue
        for result in results:
            if isinstance(result, list):
                for post in result:
                    try:
                        from backend.api.event_store import SCRAPE_QUEUE
                        if SCRAPE_QUEUE:
                            await SCRAPE_QUEUE.put(post)
                        else:
                            logger.warning("SCRAPE_QUEUE not initialized")
                    except asyncio.QueueFull:
                        logger.warning("Scrape queue full, dropping post")

    async def run_dynamic(self, interval_minutes: int = 5):
        """Run continuous scraping with dynamic coin tracking."""
        self.running = True
        logger.info("Layer B scraper started with dynamic coin tracking")
        print("Layer B scraper started with dynamic coin tracking")

        coin_last_scraped = {}

        while self.running:
            try:
                from backend.api.event_store import get_active_coins
                from core.coin_metadata import get_sentiment_keywords

                active_coins = get_active_coins()
                now = datetime.utcnow()
                scraped_any = False

                if active_coins:
                    for coin in active_coins:
                        last_scraped = coin_last_scraped.get(coin)
                        
                        if not last_scraped or (now - last_scraped).total_seconds() >= (interval_minutes * 60):
                            keywords = get_sentiment_keywords(coin)
                            print(f"\n[Layer B] Processing {coin} with keywords: {keywords}")
                            await self.scrape_all_sources(coin, keywords)
                            coin_last_scraped[coin] = datetime.utcnow()
                            scraped_any = True
                            await asyncio.sleep(2)
                            
                if not scraped_any:
                    await asyncio.sleep(5)
                else:
                    print(f"\n[Layer B] Scrape cycle finished. Checking for new coins every 5s...")
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in Layer B scraper: {e}")
                print(f"Error in Layer B scraper: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop the scraper."""
        self.running = False
        await self.client.aclose()

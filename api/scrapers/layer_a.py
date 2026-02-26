"""Layer A Scraper - Authoritative sources (RSS feeds, official blogs)."""
import asyncio
import httpx
import feedparser
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LayerAScraper:
    """Scraper for authoritative crypto news sources."""

    # RSS feeds for major crypto news sites
    RSS_FEEDS = {
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "cointelegraph": "https://cointelegraph.com/rss",
        "decrypt": "https://decrypt.co/feed",
        "theblock": "https://www.theblock.co/rss.xml",
        "bitcoinmagazine": "https://bitcoinmagazine.com/.rss/full/",
    }

    # Official blog feeds
    BLOG_FEEDS = {
        "binance": "https://www.binance.com/en/blog/rss.xml",
        "coinbase": "https://blog.coinbase.com/feed",
        "ethereum": "https://blog.ethereum.org/feed.xml",
    }

    def __init__(self, scrape_queue: asyncio.Queue = None):
        self.scrape_queue = scrape_queue  # Keep for compatibility, but will use event_store
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.running = False

    async def fetch_full_article(self, url: str) -> tuple:
        """Fetch full article content and image from URL."""
        try:
            response = await self.client.get(url, timeout=15.0)
            response.raise_for_status()

            # Basic HTML content extraction (remove tags)
            import re
            html = response.text

            # Extract image URL (try multiple patterns)
            image_url = None

            # Try Open Graph image
            og_image = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if og_image:
                image_url = og_image.group(1)

            # Try Twitter card image
            if not image_url:
                twitter_image = re.search(r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                if twitter_image:
                    image_url = twitter_image.group(1)

            # Try first img tag in article/main content
            if not image_url:
                article_img = re.search(r'<article[^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']', html, re.DOTALL | re.IGNORECASE)
                if article_img:
                    image_url = article_img.group(1)

            # Try any img tag as fallback
            if not image_url:
                any_img = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
                if any_img:
                    image_url = any_img.group(1)

            # Remove script and style tags
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

            # Remove navigation, header, footer, sidebar elements
            html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<aside[^>]*>.*?</aside>', '', html, flags=re.DOTALL | re.IGNORECASE)

            # Remove common navigation/menu classes
            html = re.sub(r'<div[^>]*class=["\'][^"\']*(?:nav|menu|header|footer|sidebar|price|ticker)[^"\']*["\'][^>]*>.*?</div>', '', html, flags=re.DOTALL | re.IGNORECASE)

            # Try to extract just the article content
            content = ""

            # Try article tag first
            article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
            if article_match:
                content = article_match.group(1)
            else:
                # Try main tag
                main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
                if main_match:
                    content = main_match.group(1)
                else:
                    # Try body as fallback
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
                    if body_match:
                        content = body_match.group(1)
                    else:
                        content = html

            # Remove all HTML tags
            content = re.sub(r'<[^>]+>', ' ', content)

            # Remove excessive whitespace and clean up
            content = re.sub(r'\s+', ' ', content).strip()

            # Remove common noise patterns (coin prices, tickers)
            content = re.sub(r'(?:BTC|ETH|XRP|SOL|USDC|USDT)\s+\$[\d,]+\.?\d*\s+[\d.]+%', '', content)
            content = re.sub(r'\$[\d,]+\.?\d*\s+[\d.]+%', '', content)

            # Limit to reasonable article length
            if len(content) > 10000:
                content = content[:10000]

            return (content, image_url)  # Return tuple (content, image_url)

        except Exception as e:
            logger.warning(f"Could not fetch full article from {url}: {e}")
            return ("", None)

    async def scrape_rss_feed(self, source: str, url: str, coin: str) -> List[Dict[str, Any]]:
        """Scrape a single RSS feed."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()

            feed = feedparser.parse(response.text)
            articles = []

            for entry in feed.entries[:20]:  # Limit to 20 most recent
                # Check if article mentions the coin
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                text = f"{title}. {summary}"

                if coin.lower() in text.lower():
                    article_url = entry.get("link", "")

                    # Try to get image from RSS feed first
                    image_url = None
                    if hasattr(entry, 'media_content') and entry.media_content:
                        image_url = entry.media_content[0].get('url')
                    elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                        image_url = entry.media_thumbnail[0].get('url')
                    elif hasattr(entry, 'enclosures') and entry.enclosures:
                        for enclosure in entry.enclosures:
                            if enclosure.get('type', '').startswith('image/'):
                                image_url = enclosure.get('href')
                                break

                    # Fetch full article content and image
                    full_content, fetched_image = await self.fetch_full_article(article_url)

                    # Use fetched image if RSS didn't have one
                    if not image_url:
                        image_url = fetched_image

                    articles.append({
                        "coin": coin,
                        "title": title,
                        "summary": summary,
                        "text": text[:1000],  # For embedding
                        "full_content": full_content if full_content else summary,
                        "image_url": image_url,
                        "source_type": "layer_a",
                        "source": f"{source}_rss",
                        "platform_id": source,
                        "timestamp": datetime.utcnow(),
                        "url": article_url,
                        "engagement_count": 0,  # RSS feeds don't have engagement metrics
                        "credibility_weight": 0.6  # Layer A weight
                    })

            return articles

        except Exception as e:
            logger.error(f"Error scraping {source} RSS: {e}")
            return []

    async def scrape_all_feeds(self, coin: str):
        """Scrape all RSS and blog feeds for a coin."""
        all_feeds = {**self.RSS_FEEDS, **self.BLOG_FEEDS}

        tasks = [
            self.scrape_rss_feed(source, url, coin)
            for source, url in all_feeds.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and push to queue
        for result in results:
            if isinstance(result, list):
                for article in result:
                    try:
                        # Import here to get the initialized queue
                        from api.event_store import SCRAPE_QUEUE
                        if SCRAPE_QUEUE:
                            await SCRAPE_QUEUE.put(article)
                        else:
                            logger.warning("SCRAPE_QUEUE not initialized")
                    except asyncio.QueueFull:
                        logger.warning("Scrape queue full, dropping article")

    async def run(self, coins: List[str], interval_minutes: int = 15):
        """
        Run continuous scraping for Layer A sources.

        Args:
            coins: List of coin names to track (e.g., ["bitcoin", "ethereum"])
            interval_minutes: Polling interval (default: 15 minutes)
        """
        self.running = True
        logger.info(f"Layer A scraper started for coins: {coins}")

        while self.running:
            try:
                for coin in coins:
                    await self.scrape_all_feeds(coin)
                    await asyncio.sleep(2)  # Small delay between coins

                # Wait for next polling interval
                await asyncio.sleep(interval_minutes * 60)

            except Exception as e:
                logger.error(f"Error in Layer A scraper: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def run_dynamic(self, interval_minutes: int = 15):
        """
        Run continuous scraping with dynamic coin tracking.

        Scrapes coins that are actively being tracked by users.
        """
        self.running = True
        logger.info("Layer A scraper started with dynamic coin tracking")
        print("Layer A scraper started with dynamic coin tracking")  # Console output

        while self.running:
            try:
                # Import here to avoid circular dependency
                from api.event_store import get_active_coins

                active_coins = get_active_coins()

                if active_coins:
                    logger.info(f"Layer A scraping {len(active_coins)} coins: {active_coins}")
                    print(f"Layer A scraping {len(active_coins)} coins: {active_coins}")
                    for coin in active_coins:
                        await self.scrape_all_feeds(coin)
                        await asyncio.sleep(2)  # Small delay between coins

                    # Wait for next polling interval after scraping
                    logger.info(f"Layer A: Waiting {interval_minutes} minutes until next scrape")
                    print(f"Layer A: Waiting {interval_minutes} minutes until next scrape")
                    await asyncio.sleep(interval_minutes * 60)
                else:
                    # No coins yet, check again in 30 seconds
                    logger.debug("No active coins to scrape")
                    print("Layer A: No active coins to scrape yet, checking again in 30s")
                    await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in Layer A scraper: {e}")
                print(f"Error in Layer A scraper: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def stop(self):
        """Stop the scraper."""
        self.running = False
        await self.client.aclose()

"""Layer A Scraper - Authoritative sources (RSS feeds, official blogs)."""
import asyncio
import html
import httpx
import feedparser
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _safe_print(message: str):
    """Print safely on terminals with non-UTF-8 encodings (e.g., Windows cp1252)."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", errors="replace").decode("ascii"))


class LayerAScraper:
    """Scraper for authoritative crypto news sources."""

    ARTICLE_CACHE_TTL_SECONDS = 1800
    ARTICLE_FETCH_CONCURRENCY = 6
    MAX_MATCHED_ENTRIES_PER_FEED = 10
    # Full article extraction is expensive. Keep it on-demand via article detail fetches, but prefetch a few.
    MAX_FULL_ARTICLE_FETCHES_PER_FEED = 2

    # RSS feeds for major crypto news sites
    RSS_FEEDS = {
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "cointelegraph": "https://cointelegraph.com/rss",
        "decrypt": "https://decrypt.co/feed",
        "bitcoinmagazine": "https://bitcoinmagazine.com/feed",
        "cryptoslate": "https://cryptoslate.com/feed/",
        "newsbtc": "https://www.newsbtc.com/feed/",
        "blockworks": "https://blockworks.co/feed",
        "dailyhodl": "https://dailyhodl.com/feed/",
    }

    # Official blog feeds
    BLOG_FEEDS = {
        "binance": "https://www.binance.com/en/blog/rss.xml",
        "ethereum": "https://blog.ethereum.org/feed.xml",
    }

    def __init__(self, scrape_queue: asyncio.Queue = None):
        self.scrape_queue = scrape_queue  # Keep for compatibility, but will use event_store
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        )
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=limits,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, text/html;q=0.8, */*;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        self.article_cache: Dict[str, Tuple[datetime, str, Optional[str]]] = {}
        self.article_fetch_semaphore = asyncio.Semaphore(self.ARTICLE_FETCH_CONCURRENCY)
        self.running = False

    def _clean_text(self, value: Optional[str]) -> str:
        text = html.unescape(value or "")
        import re
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _clean_block_text(self, value: Optional[str]) -> str:
        text = html.unescape(value or "").replace("\r\n", "\n")
        import re
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    async def _extract_best_content(self, html_text: str) -> Tuple[str, Optional[str]]:
        """Extract the most article-like content block from an HTML page."""
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(
            None,
            lambda: BeautifulSoup(html_text, "lxml")
        )

        for tag in soup(["script", "style", "noscript", "iframe", "svg", "form"]):
            tag.decompose()

        image_url = None
        for selector, attr in (
            ('meta[property="og:image"]', "content"),
            ('meta[name="twitter:image"]', "content"),
        ):
            node = soup.select_one(selector)
            if node and node.get(attr):
                image_url = node.get(attr)
                break

        selectors = [
            "article",
            "[itemprop='articleBody']",
            ".article-content",
            ".entry-content",
            ".post-content",
            ".article-body",
            ".article__content",
            ".story-content",
            ".td-post-content",
            "main",
            ".content",
        ]

        candidates = []
        for selector in selectors:
            candidates.extend(soup.select(selector))

        if not candidates and soup.body:
            candidates = [soup.body]

        def score(node) -> int:
            return len(node.get_text(" ", strip=True))

        best = max(candidates, key=score, default=None)
        if best is None:
            return ("", image_url)

        junk_selectors = [
            "nav",
            "header",
            "footer",
            "aside",
            ".related",
            ".recommended",
            ".newsletter",
            ".subscribe",
            ".social",
            ".share",
            ".comments",
            ".comment",
            ".advertisement",
            ".advertising",
            ".promo",
            ".ticker",
            ".breadcrumb",
            ".breadcrumbs",
            ".author-box",
            ".tags",
        ]
        for selector in junk_selectors:
            for node in best.select(selector):
                node.decompose()

        paragraphs = []
        seen = set()
        for node in best.find_all(["p", "h2", "h3", "li"]):
            paragraph = self._clean_text(node.get_text(" ", strip=True))
            if len(paragraph) < 40:
                continue
            key = paragraph.lower()
            if key in seen:
                continue
            seen.add(key)
            paragraphs.append(paragraph)

        if not paragraphs:
            fallback = self._clean_text(best.get_text("\n", strip=True))
            return (fallback[:15000], image_url)

        return ("\n\n".join(paragraphs)[:15000], image_url)

    async def fetch_full_article(self, url: str) -> tuple:
        """Fetch full article content and image from URL."""
        # Intercept and decode Google News URLs to fetch the actual content
        if url and "news.google.com" in url and "articles/" in url:
            try:
                import base64
                import re
                payload = url.split('articles/')[1].split('?')[0]
                payload += '=' * (-len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                match = re.search(rb'(https?://[^\x00-\x1F\x7F]+)', decoded)
                if match:
                    url = match.group(1).decode('utf-8', errors='ignore')
            except Exception as e:
                logger.debug(f"Failed to extract base64 URL in fetch_full_article for {url}: {e}")
        cached = self.article_cache.get(url)
        if cached:
            cached_at, content, image_url = cached
            if (datetime.utcnow() - cached_at).total_seconds() < self.ARTICLE_CACHE_TTL_SECONDS:
                return (content, image_url)

        try:
            async with self.article_fetch_semaphore:
                response = await self.client.get(url, timeout=12.0)
                response.raise_for_status()
            content, image_url = await self._extract_best_content(response.text)
            content = self._clean_block_text(content)

            self.article_cache[url] = (datetime.utcnow(), content, image_url)
            return (content, image_url)

        except Exception as e:
            logger.warning(f"Could not fetch full article from {url}: {e}")
            return ("", None)

    async def scrape_rss_feed(self, source: str, url: str, coin: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Scrape a single RSS feed.

        Args:
            source: Source name
            url: RSS feed URL
            coin: Primary coin identifier (for storage)
            keywords: List of keywords to match (name, symbol, aliases)
        """
        if keywords is None:
            keywords = [coin]

        try:
            logger.info(f"[{source}] Fetching RSS feed: {url}")
            _safe_print(f"[{source}] Fetching RSS feed for {coin} with keywords: {keywords}")

            response = await self.client.get(url)
            response.raise_for_status()

            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, response.text)
            articles = []

            total_entries = len(feed.entries)
            logger.info(f"[{source}] Found {total_entries} entries in feed")
            _safe_print(f"[{source}] Found {total_entries} entries, checking for matches...")

            # First pass: find all matching entries
            matched_entries = []
            for entry in feed.entries[:100]:  # Check up to 100 most recent entries
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                raw_text = f"{title}. {summary}"
                text = raw_text.lower()

                # Match against any keyword
                if any(keyword.lower() in text for keyword in keywords):
                    logger.info(f"[{source}] MATCH FOUND: {title[:80]}")
                    _safe_print(f"[{source}] [OK] Match: {title[:80]}")
                    matched_entries.append(entry)

            matches_found = len(matched_entries)

            # Second pass: fetch full content in parallel (limit to 10 articles per feed for speed)
            async def process_entry(entry, fetch_full_article: bool):
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                raw_text = f"{title}. {summary}"
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

                full_content = summary
                fetched_image = image_url
                if fetch_full_article and article_url:
                    full_content, fetched_image = await self.fetch_full_article(article_url)

                # Use fetched image if RSS didn't have one
                if not image_url:
                    image_url = fetched_image

                # Parse published date from RSS entry
                published_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    from time import mktime
                    published_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    from time import mktime
                    published_date = datetime.fromtimestamp(mktime(entry.updated_parsed))
                else:
                    published_date = datetime.utcnow()

                return {
                    "coin": coin,
                    "title": title,
                    "summary": summary,
                    "text": raw_text[:1000],
                    "full_content": full_content if full_content else summary,
                    "image_url": image_url,
                    "source_type": "layer_a",
                    "source": f"{source}_rss",
                    "platform_id": source,
                    "timestamp": published_date,
                    "url": article_url,
                    "engagement_count": 0,
                    "credibility_weight": 0.6
                }

            # Keep the feed broad, but only fetch a few full article bodies per source.
            if matched_entries:
                tasks = [
                    process_entry(
                        entry,
                        fetch_full_article=index < self.MAX_FULL_ARTICLE_FETCHES_PER_FEED,
                    )
                    for index, entry in enumerate(
                        matched_entries[:self.MAX_MATCHED_ENTRIES_PER_FEED]
                    )
                ]
                articles = await asyncio.gather(*tasks, return_exceptions=True)
                # Filter out exceptions
                articles = [a for a in articles if isinstance(a, dict)]

            logger.info(f"[{source}] Scraped {len(articles)} articles for {coin} (matched {matches_found}/{total_entries})")
            _safe_print(f"[{source}] [OK] Scraped {len(articles)} articles for {coin}")
            return articles

        except Exception as e:
            logger.error(f"[{source}] Error scraping RSS: {e}")
            _safe_print(f"[{source}] [ERROR] Error: {e}")
            return []

    async def scrape_all_feeds(self, coin: str, keywords: List[str] = None):
        """Scrape all RSS and blog feeds for a coin.

        Args:
            coin: Primary coin identifier (for storage)
            keywords: List of keywords to match (name, symbol, aliases)
        """
        if keywords is None:
            keywords = [coin]

        all_feeds = {**self.RSS_FEEDS, **self.BLOG_FEEDS}

        tasks = [
            self.scrape_rss_feed(source, url, coin, keywords)
            for source, url in all_feeds.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and push to queue
        total_articles = 0
        for result in results:
            if isinstance(result, list):
                for article in result:
                    try:
                        # Import here to get the initialized queue
                        from backend.api.event_store import SCRAPE_QUEUE
                        if SCRAPE_QUEUE:
                            await SCRAPE_QUEUE.put(article)
                            total_articles += 1
                        else:
                            logger.warning("SCRAPE_QUEUE not initialized")
                    except asyncio.QueueFull:
                        logger.warning("Scrape queue full, dropping article")

        if total_articles > 0:
            _safe_print(f"[Layer A] [OK] Pushed {total_articles} articles to processing queue for {coin}")
            logger.info(f"Pushed {total_articles} articles to queue for {coin}")
        else:
            _safe_print(f"[Layer A] No articles found for {coin}")
            logger.info(f"No articles found for {coin}")

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
        _safe_print("=" * 60)
        _safe_print("Layer A scraper started with dynamic coin tracking")
        _safe_print("=" * 60)

        coin_last_scraped = {}

        while self.running:
            try:
                # Import here to avoid circular dependency
                from backend.api.event_store import get_active_coins
                from core.coin_metadata import get_sentiment_keywords

                active_coins = get_active_coins()
                now = datetime.utcnow()
                scraped_any = False

                if active_coins:
                    for coin in active_coins:
                        last_scraped = coin_last_scraped.get(coin)
                        
                        # Only scrape if never scraped or interval has passed
                        if not last_scraped or (now - last_scraped).total_seconds() >= (interval_minutes * 60):
                            keywords = get_sentiment_keywords(coin)
                            _safe_print(f"\n[Layer A] Processing {coin} with keywords: {keywords}")
                            await self.scrape_all_feeds(coin, keywords)
                            coin_last_scraped[coin] = datetime.utcnow()
                            scraped_any = True
                            await asyncio.sleep(2)  # Small delay between coins
                            
                # Sleep briefly so new active coins are picked up quickly
                if not scraped_any:
                    await asyncio.sleep(5)
                else:
                    _safe_print(f"\n[Layer A] Scrape cycle finished. Checking for new coins every 5s...")
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in Layer A dynamic scraper: {e}")
                _safe_print(f"[Layer A] ERROR: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

        logger.info("Layer A scraper stopped")

    async def stop(self):
        """Stop the scraper."""
        self.running = False
        await self.client.aclose()

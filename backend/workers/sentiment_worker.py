"""Sentiment worker - Analyzes sentiment using CryptoBERT."""
import asyncio
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SentimentWorker:
    """Worker that analyzes sentiment using CryptoBERT."""

    def __init__(self, scrape_queue: asyncio.Queue, cluster_queue: asyncio.Queue):
        self.scrape_queue = scrape_queue
        self.cluster_queue = cluster_queue
        self.tokenizer = None
        self.model = None
        self.label_to_index = {
            "Bearish": 0,
            "Neutral": 1,
            "Bullish": 2,
        }
        self.running = False

    def load_model(self):
        """Load CryptoBERT model for sentiment analysis."""
        logger.info("Loading CryptoBERT model (ElKulako/cryptobert)...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("ElKulako/cryptobert")
            self.model = AutoModelForSequenceClassification.from_pretrained("ElKulako/cryptobert")
            self.model.eval()  # Set to evaluation mode
            self._load_label_mapping()
            logger.info("CryptoBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading CryptoBERT: {e}")
            raise

    def _load_label_mapping(self):
        """Read the label order from the loaded model config instead of hardcoding it."""
        config = getattr(self.model, "config", None)
        id2label = getattr(config, "id2label", None) or {}

        if not id2label:
            logger.warning("CryptoBERT config missing id2label; using default label order")
            return

        normalized: Dict[str, int] = {}
        for index, label in id2label.items():
            label_key = str(label).strip().lower()
            if label_key == "bullish":
                normalized["Bullish"] = int(index)
            elif label_key == "bearish":
                normalized["Bearish"] = int(index)
            elif label_key == "neutral":
                normalized["Neutral"] = int(index)

        if set(normalized.keys()) == {"Bullish", "Bearish", "Neutral"}:
            self.label_to_index = normalized
            logger.info(f"Loaded CryptoBERT label mapping: {self.label_to_index}")
        else:
            logger.warning(
                f"Incomplete CryptoBERT label mapping {id2label}; using default label order"
            )

    def _prepare_text(self, text: str) -> str:
        """Clean scraped content before sending it to the model."""
        cleaned = re.sub(r"<[^>]+>", " ", text)
        cleaned = re.sub(r"https?://\S+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:4000]

    def _build_analysis_text(self, item: Dict[str, Any]) -> str:
        """Combine the best available fields so sentiment uses more than a short snippet."""
        parts = []
        seen = set()

        for field in ("title", "summary", "full_content", "text"):
            value = item.get(field, "")
            if not value:
                continue

            normalized = re.sub(r"\s+", " ", str(value)).strip()
            if not normalized:
                continue

            dedupe_key = normalized.lower()
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            parts.append(normalized)

        return " ".join(parts)

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text using CryptoBERT.

        Returns:
            {
                "label": "Bullish" | "Bearish" | "Neutral",
                "polarity": float (-1 to 1),
                "confidence": float (0 to 1),
                "scores": {"Bullish": float, "Bearish": float, "Neutral": float}
            }
        """
        try:
            cleaned_text = self._prepare_text(text)
            if not cleaned_text:
                return None

            # Tokenize input
            inputs = self.tokenizer(
                cleaned_text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)[0]

            bearish_score = float(probs[self.label_to_index["Bearish"]])
            neutral_score = float(probs[self.label_to_index["Neutral"]])
            bullish_score = float(probs[self.label_to_index["Bullish"]])

            # Determine label
            scores = {
                "Bullish": bullish_score,
                "Bearish": bearish_score,
                "Neutral": neutral_score,
            }
            label, max_score = max(scores.items(), key=lambda item: item[1])

            # Calculate polarity (-1 to 1)
            # Bullish = positive, Bearish = negative, Neutral = 0
            polarity = bullish_score - bearish_score

            return {
                "label": label,
                "polarity": polarity,
                "confidence": max_score,
                "scores": scores
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            raise  # NO FALLBACK - fail fast

    async def process_item(self, item: Dict[str, Any]):
        """Process a single scraped item and analyze sentiment."""
        try:
            text = item.get("text", "")
            analysis_text = self._build_analysis_text(item)

            if not analysis_text and not text:
                logger.warning("Empty text in scraped item")
                return

            # Validate required fields
            if not item.get("coin"):
                logger.warning("Missing coin field in scraped item")
                return

            from backend.api.event_store import initialize_coin, is_item_known

            initialize_coin(item["coin"])
            if is_item_known(item["coin"], item):
                logger.debug(f"Skipping duplicate sentiment analysis for {item['coin']}")
                return

            # Analyze sentiment (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            sentiment = await loop.run_in_executor(
                None,
                self.analyze_sentiment,
                analysis_text or text
            )

            # Skip items where sentiment analysis failed
            if sentiment is None:
                logger.warning(f"Sentiment analysis failed for item, skipping")
                return

            # Add sentiment to item
            item["sentiment"] = sentiment

            # Push to cluster queue
            from backend.api.event_store import CLUSTER_QUEUE
            if CLUSTER_QUEUE:
                await CLUSTER_QUEUE.put(item)
            else:
                logger.warning("CLUSTER_QUEUE not initialized")

        except Exception as e:
            logger.error(f"Error processing item for sentiment: {e}")

    def analyze_sentiment_batch(self, texts: list) -> list:
        """Analyze multiple texts at once for better performance."""
        if not texts:
            return []

        cleaned_texts = [self._prepare_text(text) for text in texts]

        # Batch tokenization
        inputs = self.tokenizer(
            cleaned_texts,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )

        # Batch inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)

        # Process results
        results = []
        for i in range(len(texts)):
            bearish_score = float(probs[i][self.label_to_index["Bearish"]])
            neutral_score = float(probs[i][self.label_to_index["Neutral"]])
            bullish_score = float(probs[i][self.label_to_index["Bullish"]])

            scores = {
                "Bullish": bullish_score,
                "Bearish": bearish_score,
                "Neutral": neutral_score,
            }
            label, max_score = max(scores.items(), key=lambda item: item[1])
            polarity = bullish_score - bearish_score

            results.append({
                "label": label,
                "polarity": polarity,
                "confidence": max_score,
                "scores": scores
            })

        return results

    async def process_batch(self, items: list):
        """Process multiple items in a batch for efficiency."""
        if not items:
            return

        # Prepare all texts
        texts = []
        valid_items = []
        for item in items:
            analysis_text = self._build_analysis_text(item)
            text = item.get("text", "")
            if analysis_text or text:
                texts.append(analysis_text or text)
                valid_items.append(item)

        if not texts:
            return

        # Batch inference
        loop = asyncio.get_event_loop()
        sentiments = await loop.run_in_executor(
            None,
            self.analyze_sentiment_batch,
            texts
        )

        # Assign sentiments and push to cluster queue
        from backend.api.event_store import CLUSTER_QUEUE
        for item, sentiment in zip(valid_items, sentiments):
            if sentiment:
                item["sentiment"] = sentiment
                if CLUSTER_QUEUE:
                    await CLUSTER_QUEUE.put(item)

    async def run(self):
        """Run the sentiment worker continuously with batch processing."""
        self.running = True

        # Load model on startup
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.load_model)

        logger.info("Sentiment worker started with batch processing")
        print("=" * 60)
        print("CryptoBERT Sentiment Worker started (batch mode)")
        print("=" * 60)

        BATCH_SIZE = 10
        BATCH_TIMEOUT = 2.0  # seconds

        while self.running:
            try:
                from backend.api.event_store import SCRAPE_QUEUE

                if not SCRAPE_QUEUE:
                    await asyncio.sleep(1)
                    continue

                # Collect batch
                batch = []
                deadline = asyncio.get_event_loop().time() + BATCH_TIMEOUT

                while len(batch) < BATCH_SIZE:
                    timeout = max(0.1, deadline - asyncio.get_event_loop().time())
                    try:
                        item = await asyncio.wait_for(SCRAPE_QUEUE.get(), timeout=timeout)
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break

                if batch:
                    logger.debug(f"Processing batch of {len(batch)} articles")
                    await self.process_batch(batch)
                    await asyncio.sleep(0.1)  # Throttle

            except Exception as e:
                logger.error(f"Error in sentiment worker: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """Stop the worker."""
        self.running = False
        logger.info("Sentiment worker stopped")

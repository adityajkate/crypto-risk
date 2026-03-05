"""Embedding worker - Generates sentence embeddings using all-MiniLM-L6-v2."""
import asyncio
from sentence_transformers import SentenceTransformer
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EmbeddingWorker:
    """Worker that generates embeddings from scraped text."""

    def __init__(self, scrape_queue: asyncio.Queue, cluster_queue: asyncio.Queue):
        self.scrape_queue = scrape_queue
        self.cluster_queue = cluster_queue
        self.model = None
        self.running = False

    def load_model(self):
        """Load the sentence transformer model."""
        logger.info("Loading all-MiniLM-L6-v2 model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")

    async def process_item(self, item: Dict[str, Any]):
        """Process a single scraped item and generate embedding."""
        try:
            text = item.get("text", "")

            if not text:
                logger.warning("Empty text in scraped item")
                return

            # Validate required fields
            if not item.get("coin"):
                logger.warning("Missing coin field in scraped item")
                return

            # Generate embedding (384-dimensional vector)
            # Run in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self.model.encode,
                text
            )

            # Add embedding to item
            item["embedding"] = embedding

            # Push to cluster queue
            from api.event_store import CLUSTER_QUEUE
            if CLUSTER_QUEUE:
                await CLUSTER_QUEUE.put(item)
            else:
                logger.warning("CLUSTER_QUEUE not initialized")

        except Exception as e:
            logger.error(f"Error processing item for embedding: {e}")

    async def run(self):
        """Run the embedding worker continuously."""
        self.running = True

        # Load model on startup
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.load_model)

        logger.info("Embedding worker started")
        print("=" * 60)
        print("Embedding worker started and ready")
        print("=" * 60)

        processed_count = 0
        while self.running:
            try:
                # Import queues from event_store to get initialized references
                from api.event_store import SCRAPE_QUEUE, CLUSTER_QUEUE

                if not SCRAPE_QUEUE:
                    await asyncio.sleep(1)
                    continue

                # Get item from scrape queue (with timeout)
                item = await asyncio.wait_for(
                    SCRAPE_QUEUE.get(),
                    timeout=1.0
                )

                processed_count += 1
                coin = item.get('coin', 'unknown')
                source = item.get('source', 'unknown')
                print(f"[Embedding Worker] Processing article #{processed_count} for {coin} from {source}")

                # Process the item (will use CLUSTER_QUEUE from event_store)
                await self.process_item(item)

            except asyncio.TimeoutError:
                # No items in queue, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error in embedding worker: {e}")
                print(f"[Embedding Worker] ERROR: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """Stop the worker."""
        self.running = False
        logger.info("Embedding worker stopped")

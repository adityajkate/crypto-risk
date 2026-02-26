"""Clustering worker - Assigns embeddings to clusters and calculates event scores."""
import asyncio
import numpy as np
from datetime import datetime
import logging
from typing import Dict, Any, Optional
from api.event_store import (
    EVENT_STORE,
    initialize_coin,
    prune_stale_data,
    calculate_event_score,
    calculate_mention_velocity,
    update_global_metrics
)

logger = logging.getLogger(__name__)


class ClusteringWorker:
    """Worker that performs streaming clustering on embeddings."""

    # Cosine similarity threshold for cluster assignment
    SIMILARITY_THRESHOLD = 0.85

    def __init__(self, cluster_queue: asyncio.Queue):
        self.cluster_queue = cluster_queue
        self.running = False
        self.next_cluster_id = 0

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def find_nearest_cluster(
        self,
        embedding: np.ndarray,
        coin: str
    ) -> Optional[int]:
        """
        Find the nearest cluster for an embedding.

        Returns cluster_id if similarity > threshold, else None.
        """
        if coin not in EVENT_STORE:
            return None

        clusters = EVENT_STORE[coin]["clusters"]

        if not clusters:
            return None

        best_cluster_id = None
        best_similarity = -1.0

        for cluster_id, cluster_data in clusters.items():
            centroid = cluster_data["centroid"]
            similarity = self.cosine_similarity(embedding, centroid)

            if similarity > best_similarity:
                best_similarity = similarity
                best_cluster_id = cluster_id

        # Only return cluster if similarity exceeds threshold
        if best_similarity >= self.SIMILARITY_THRESHOLD:
            return best_cluster_id

        return None

    def update_centroid(self, cluster_data: Dict[str, Any]):
        """Update cluster centroid as running average of member embeddings."""
        members = cluster_data["members"]

        if not members:
            return

        # Calculate mean of all embeddings
        embeddings = np.array([m["embedding"] for m in members])
        centroid = np.mean(embeddings, axis=0)

        cluster_data["centroid"] = centroid

    def create_new_cluster(self, coin: str, item: Dict[str, Any]) -> int:
        """Create a new cluster with the given item."""
        cluster_id = self.next_cluster_id
        self.next_cluster_id += 1

        EVENT_STORE[coin]["clusters"][cluster_id] = {
            "centroid": item["embedding"].copy(),
            "members": [item],
            "event_score": 0.0,
            "mention_velocity": 0.0
        }

        logger.info(f"Created new cluster {cluster_id} for {coin}")
        return cluster_id

    def add_to_cluster(self, coin: str, cluster_id: int, item: Dict[str, Any]):
        """Add item to existing cluster and update metrics."""
        cluster_data = EVENT_STORE[coin]["clusters"][cluster_id]

        # Add member
        cluster_data["members"].append(item)

        # Update centroid
        self.update_centroid(cluster_data)

        # Recalculate metrics
        cluster_data["event_score"] = calculate_event_score(cluster_data)
        cluster_data["mention_velocity"] = calculate_mention_velocity(cluster_data["members"])

    async def process_item(self, item: Dict[str, Any]):
        """Process a single item with embedding."""
        try:
            coin = item.get("coin")
            embedding = item.get("embedding")

            if not coin:
                logger.warning("Missing coin in item")
                return

            if embedding is None:
                logger.warning("Missing embedding in item")
                return

            # Validate required fields
            required_fields = ["text", "source_type", "source", "timestamp", "platform_id"]
            for field in required_fields:
                if field not in item:
                    logger.warning(f"Missing required field '{field}' in item for {coin}")
                    return

            # Initialize coin if needed
            initialize_coin(coin)

            # Prune stale data (continuous cleanup)
            prune_stale_data(coin, max_age_minutes=180)

            # Find nearest cluster
            cluster_id = self.find_nearest_cluster(embedding, coin)

            if cluster_id is not None:
                # Add to existing cluster
                self.add_to_cluster(coin, cluster_id, item)
                logger.debug(f"Added to cluster {cluster_id} for {coin}")
            else:
                # Create new cluster
                cluster_id = self.create_new_cluster(coin, item)

            # Update global metrics
            update_global_metrics(coin)

        except Exception as e:
            logger.error(f"Error processing item in clustering worker: {e}")

    async def run(self):
        """Run the clustering worker continuously."""
        self.running = True
        logger.info("Clustering worker started")

        while self.running:
            try:
                # Import queue from event_store to get initialized reference
                from api.event_store import CLUSTER_QUEUE

                if not CLUSTER_QUEUE:
                    await asyncio.sleep(1)
                    continue

                # Get item from cluster queue (with timeout)
                item = await asyncio.wait_for(
                    CLUSTER_QUEUE.get(),
                    timeout=1.0
                )

                # Process the item
                await self.process_item(item)

            except asyncio.TimeoutError:
                # No items in queue, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error in clustering worker: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """Stop the worker."""
        self.running = False
        logger.info("Clustering worker stopped")

"""Clustering worker - Assigns articles to clusters using HDBSCAN."""
import asyncio
import numpy as np
from datetime import datetime
import logging
from typing import Dict, Any, Optional
import hdbscan
from sklearn.preprocessing import normalize
from backend.api.event_store import (
    EVENT_STORE,
    get_all_items,
    initialize_coin,
    is_item_known,
    prune_stale_data,
    remember_item,
    update_global_metrics
)

logger = logging.getLogger(__name__)


class ClusteringWorker:
    """Worker that performs adaptive clustering using HDBSCAN."""

    def __init__(self, cluster_queue: asyncio.Queue):
        self.cluster_queue = cluster_queue
        self.running = False
        self.next_cluster_id = 0

        # HDBSCAN parameters
        self.min_cluster_size = 3  # Minimum articles to form a cluster
        self.min_samples = 2  # Core point threshold
        self.reclustering_threshold = 100  # Recluster after N new articles

    def calculate_sentiment_score(self, members: list) -> Dict[str, Any]:
        """
        Calculate aggregate sentiment for a cluster.

        Returns:
            {
                "polarity": float (-1 to 1),
                "label": str ("Bullish", "Bearish", "Neutral"),
                "confidence": float (0 to 1),
                "distribution": {"Bullish": float, "Bearish": float, "Neutral": float}
            }
        """
        if not members:
            return None

        # Aggregate sentiment from all members
        polarities = []
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        confidences = []

        for member in members:
            sentiment = member.get("sentiment")
            if not sentiment:
                # Skip members without sentiment data
                continue

            polarity = sentiment.get("polarity", 0.0)
            label = sentiment.get("label", "Neutral")
            confidence = sentiment.get("confidence", 0.0)

            polarities.append(polarity)
            confidences.append(confidence)

            if label == "Bullish":
                bullish_count += 1
            elif label == "Bearish":
                bearish_count += 1
            else:
                neutral_count += 1

        if not polarities:
            # No valid sentiment data found
            return None

        # Calculate weighted average polarity
        total_members = len(members)
        avg_polarity = sum(polarities) / total_members
        avg_confidence = sum(confidences) / total_members

        # Determine overall label
        if bullish_count > bearish_count and bullish_count > neutral_count:
            label = "Bullish"
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            label = "Bearish"
        else:
            label = "Neutral"

        # Calculate distribution
        distribution = {
            "Bullish": float(bullish_count / total_members),
            "Bearish": float(bearish_count / total_members),
            "Neutral": float(neutral_count / total_members)
        }

        return {
            "polarity": float(avg_polarity),
            "label": label,
            "confidence": float(avg_confidence),
            "distribution": distribution
        }

    def calculate_unified_score(
        self,
        cluster_data: Dict[str, Any],
        fear_greed_normalized: float = None,
        google_trends_normalized: float = None
    ) -> float:
        """
        Calculate unified sentiment score using the new formula.

        Formula (dynamic weights based on available data):
        score = (
            sentiment_polarity * weight_sentiment
            + mention_velocity_norm * weight_velocity
            + platform_diversity * weight_diversity
            + fear_greed_norm * weight_fg (if available)
            + google_trends_norm * weight_trends (if available)
        ) × recency_weight

        Returns:
            float: Unified score (typically -1 to 1 range), or None if insufficient data
        """
        members = cluster_data.get("members", [])

        if not members:
            return None

        # 1. Sentiment polarity (35% base)
        sentiment = cluster_data.get("sentiment")
        if not sentiment:
            return None
        sentiment_polarity = sentiment.get("polarity", 0.0)

        # 2. Mention velocity (25% base)
        now = datetime.utcnow()
        time_window_hours = 3.0
        mention_velocity = len(members) / time_window_hours
        # Normalize to 0-1 scale (assume max 50 mentions/hour = 1.0)
        mention_velocity_norm = min(mention_velocity / 50.0, 1.0)

        # 3. Platform diversity (15% base)
        platforms = set(m["platform_id"] for m in members)
        platform_diversity = len(platforms) / 10.0  # Assume max 10 platforms

        # 4. Fear & Greed (15% if available)
        has_fear_greed = fear_greed_normalized is not None
        fear_greed_norm = fear_greed_normalized if has_fear_greed else 0.0

        # 5. Google Trends (10% if available)
        has_google_trends = google_trends_normalized is not None
        google_trends_norm = google_trends_normalized if has_google_trends else 0.0

        # 6. Recency weight (exponential decay)
        timestamps = [m["timestamp"] for m in members]
        avg_age_minutes = sum((now - ts).total_seconds() / 60 for ts in timestamps) / len(timestamps)
        recency_weight = np.exp(-avg_age_minutes / 60.0)  # Decay over 1 hour

        # Calculate dynamic weights (redistribute missing signal weights)
        base_weights = {
            "sentiment": 0.35,
            "velocity": 0.25,
            "diversity": 0.15,
            "fear_greed": 0.15 if has_fear_greed else 0.0,
            "trends": 0.10 if has_google_trends else 0.0
        }

        # Redistribute missing weights proportionally
        total_weight = sum(base_weights.values())
        if total_weight < 1.0:
            # Redistribute to sentiment, velocity, and diversity
            missing = 1.0 - total_weight
            base_weights["sentiment"] += missing * 0.5
            base_weights["velocity"] += missing * 0.3
            base_weights["diversity"] += missing * 0.2

        # Calculate unified score
        unified_score = (
            sentiment_polarity * base_weights["sentiment"]
            + mention_velocity_norm * base_weights["velocity"]
            + platform_diversity * base_weights["diversity"]
            + fear_greed_norm * base_weights["fear_greed"]
            + google_trends_norm * base_weights["trends"]
        ) * recency_weight

        return float(unified_score)

    def perform_clustering(self, coin: str, embeddings: np.ndarray, items: list):
        """
        Perform HDBSCAN clustering on embeddings.

        Args:
            coin: Coin identifier
            embeddings: Array of embeddings (N x D)
            items: List of article items corresponding to embeddings
        """
        if len(embeddings) < self.min_cluster_size:
            # Not enough data for clustering, treat all as noise
            logger.debug(f"Not enough items for clustering {coin}: {len(embeddings)}")
            return

        try:
            # Normalize embeddings for better clustering
            embeddings_norm = normalize(embeddings, norm='l2')

            # Perform HDBSCAN clustering
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=self.min_samples,
                metric='euclidean',
                cluster_selection_method='eom'
            )

            cluster_labels = clusterer.fit_predict(embeddings_norm)

            # Organize items by cluster
            clusters = {}
            noise_items = []

            for idx, label in enumerate(cluster_labels):
                if label == -1:
                    # Noise/outlier
                    noise_items.append(items[idx])
                else:
                    if label not in clusters:
                        clusters[label] = []
                    clusters[label].append(items[idx])

            # Update EVENT_STORE with new clusters
            EVENT_STORE[coin]["clusters"] = {}

            for cluster_id, cluster_members in clusters.items():
                # Calculate sentiment for cluster
                sentiment = self.calculate_sentiment_score(cluster_members)

                # Skip clusters without valid sentiment
                if sentiment is None:
                    continue

                # Get Fear & Greed and Google Trends (from global cache if available)
                from backend.api.event_store import get_fear_greed_normalized, get_google_trends_normalized
                fear_greed_norm = get_fear_greed_normalized()
                google_trends_norm = get_google_trends_normalized(coin)

                # Store cluster (convert cluster_id to int to avoid numpy types)
                EVENT_STORE[coin]["clusters"][int(cluster_id)] = {
                    "members": cluster_members,
                    "sentiment": sentiment,
                    "unified_score": None,  # Will be calculated below
                    "mention_velocity": float(len(cluster_members) / 3.0)
                }

                # Calculate unified score
                unified_score = self.calculate_unified_score(
                    EVENT_STORE[coin]["clusters"][int(cluster_id)],
                    fear_greed_norm,
                    google_trends_norm
                )
                EVENT_STORE[coin]["clusters"][int(cluster_id)]["unified_score"] = unified_score

            # Handle noise items (create individual clusters or discard)
            if noise_items:
                logger.debug(f"Found {len(noise_items)} noise items for {coin}")
                # For now, discard noise items
                # Could optionally create singleton clusters

            logger.info(f"Clustered {len(items)} items into {len(clusters)} clusters for {coin}")

        except Exception as e:
            logger.error(f"Error performing HDBSCAN clustering: {e}")

    async def process_item(self, item: Dict[str, Any]):
        """Process a single item with sentiment."""
        try:
            coin = item.get("coin")
            sentiment = item.get("sentiment")

            if not coin:
                logger.warning("Missing coin in item")
                return

            if not sentiment:
                logger.warning("Missing sentiment in item")
                return

            # Validate required fields
            required_fields = ["text", "source_type", "source", "timestamp", "platform_id"]
            for field in required_fields:
                if field not in item:
                    logger.warning(f"Missing required field '{field}' in item for {coin}")
                    return

            # Initialize coin if needed
            initialize_coin(coin)

            # Prune stale data (7 days retention to match history endpoints)
            prune_stale_data(coin, max_age_minutes=10080, persist_changes=False)

            # Skip duplicates so repeated scraper cycles do not erase or inflate the feed
            if is_item_known(coin, item):
                logger.debug(f"Skipping duplicate item for {coin}: {item.get('url', '')}")
                return

            # Add item to temporary buffer for batch clustering
            if "pending_items" not in EVENT_STORE[coin]:
                EVENT_STORE[coin]["pending_items"] = []

            EVENT_STORE[coin]["pending_items"].append(item)
            remember_item(coin, item)

            # Check if we should recluster
            pending_count = len(EVENT_STORE[coin]["pending_items"])

            if pending_count >= self.reclustering_threshold:
                # Recluster against the full retained window so previous feed items stay available.
                all_items = get_all_items(coin)

                # Extract embeddings (we need to generate them from sentiment model)
                # For now, use sentiment scores as simple features
                embeddings = []
                for it in all_items:
                    sent = it.get("sentiment")
                    if not sent:
                        # Skip items without sentiment
                        continue
                    # Create simple feature vector from sentiment
                    feature = [
                        sent.get("polarity", 0.0),
                        sent.get("confidence", 0.0),
                        sent.get("scores", {}).get("Bullish", 0.0),
                        sent.get("scores", {}).get("Bearish", 0.0),
                        sent.get("scores", {}).get("Neutral", 0.0)
                    ]
                    embeddings.append(feature)

                if len(embeddings) < self.min_cluster_size:
                    logger.debug(f"Not enough items with sentiment for clustering {coin}: {len(embeddings)}")
                    return

                embeddings = np.array(embeddings)

                # Perform clustering
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.perform_clustering,
                    coin,
                    embeddings,
                    all_items
                )

                # Clear pending items
                EVENT_STORE[coin]["pending_items"] = []

            # Update global metrics
            update_global_metrics(coin)

        except Exception as e:
            logger.error(f"Error processing item in clustering worker: {e}")

    async def run(self):
        """Run the clustering worker continuously."""
        self.running = True
        logger.info("HDBSCAN Clustering worker started")
        print("=" * 60)
        print("HDBSCAN Clustering worker started and ready")
        print("=" * 60)

        processed_count = 0
        while self.running:
            try:
                from backend.api.event_store import CLUSTER_QUEUE

                if not CLUSTER_QUEUE:
                    await asyncio.sleep(1)
                    continue

                # Get item from cluster queue (with timeout)
                item = await asyncio.wait_for(
                    CLUSTER_QUEUE.get(),
                    timeout=1.0
                )

                processed_count += 1
                coin = item.get('coin', 'unknown')
                source = item.get('source', 'unknown')
                sentiment = item.get('sentiment')
                sentiment_label = sentiment.get('label', 'Unknown') if sentiment else 'No Sentiment'
                logger.debug(f"Processing article #{processed_count} for {coin} from {source} - Sentiment: {sentiment_label}")

                # Process the item
                await self.process_item(item)

                # Throttle to prevent CPU spikes
                await asyncio.sleep(0.05)

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

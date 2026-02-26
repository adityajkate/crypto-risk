"""In-memory event store for real-time sentiment tracking."""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import numpy as np
from collections import defaultdict


# Global in-memory state
EVENT_STORE: Dict[str, Dict[str, Any]] = {}

# asyncio queues for inter-worker communication
SCRAPE_QUEUE: asyncio.Queue = None
CLUSTER_QUEUE: asyncio.Queue = None

# Track which coins are actively being monitored
ACTIVE_COINS: Set[str] = set()


def initialize_queues():
    """Initialize asyncio queues on startup."""
    global SCRAPE_QUEUE, CLUSTER_QUEUE
    SCRAPE_QUEUE = asyncio.Queue(maxsize=10000)
    CLUSTER_QUEUE = asyncio.Queue(maxsize=5000)


def add_coin_to_tracking(coin: str):
    """Add a coin to active tracking list."""
    coin = coin.lower()
    ACTIVE_COINS.add(coin)
    initialize_coin(coin)


def get_active_coins() -> List[str]:
    """Get list of actively tracked coins."""
    return list(ACTIVE_COINS)


def initialize_coin(coin: str):
    """Initialize event store structure for a coin."""
    if coin not in EVENT_STORE:
        EVENT_STORE[coin] = {
            "clusters": {},
            "last_updated": datetime.utcnow(),
            "global_metrics": {
                "total_mentions": 0,
                "weighted_event_score": 0.0,
                "layer_a_weight": 0.0,
                "layer_b_weight": 0.0,
                "recency_decay_applied": True
            }
        }


def get_coin_data(coin: str) -> Optional[Dict[str, Any]]:
    """Get event store data for a coin."""
    return EVENT_STORE.get(coin)


def calculate_event_score(cluster_data: Dict[str, Any]) -> float:
    """
    Calculate event score for a cluster.

    Formula: (mention_velocity * platform_diversity * avg_engagement) * recency_weight
    """
    members = cluster_data.get("members", [])

    if not members:
        return 0.0

    # Calculate mention velocity (posts per hour)
    now = datetime.utcnow()
    time_window_hours = 3.0  # 180 minutes = 3 hours
    mention_velocity = len(members) / time_window_hours

    # Calculate platform diversity (unique platforms / total possible)
    platforms = set(m["platform_id"] for m in members)
    platform_diversity = len(platforms) / 10.0  # Assume max 10 platforms

    # Calculate average engagement
    total_engagement = sum(m.get("engagement_count", 0) for m in members)
    avg_engagement = total_engagement / len(members) if members else 0.0

    # Calculate recency weight (exponential decay)
    timestamps = [m["timestamp"] for m in members]
    avg_age_minutes = sum((now - ts).total_seconds() / 60 for ts in timestamps) / len(timestamps)
    recency_weight = np.exp(-avg_age_minutes / 60.0)  # Decay over 1 hour

    # Final event score
    event_score = (mention_velocity * platform_diversity * avg_engagement) * recency_weight

    return float(event_score)


def calculate_mention_velocity(members: List[Dict[str, Any]]) -> float:
    """Calculate mention velocity (posts per hour)."""
    if not members:
        return 0.0

    time_window_hours = 3.0  # 180 minutes
    return len(members) / time_window_hours


def prune_stale_data(coin: str, max_age_minutes: int = 180):
    """
    Remove members older than max_age_minutes from all clusters.
    Called continuously by clustering worker.
    """
    if coin not in EVENT_STORE:
        return

    now = datetime.utcnow()
    cutoff_time = now - timedelta(minutes=max_age_minutes)

    clusters = EVENT_STORE[coin]["clusters"]
    clusters_to_remove = []

    for cluster_id, cluster_data in clusters.items():
        # Filter out stale members
        cluster_data["members"] = [
            m for m in cluster_data["members"]
            if m["timestamp"] > cutoff_time
        ]

        # If cluster is empty, mark for removal
        if not cluster_data["members"]:
            clusters_to_remove.append(cluster_id)
        else:
            # Recalculate cluster metrics
            cluster_data["event_score"] = calculate_event_score(cluster_data)
            cluster_data["mention_velocity"] = calculate_mention_velocity(cluster_data["members"])

    # Remove empty clusters
    for cluster_id in clusters_to_remove:
        del clusters[cluster_id]

    # Update global metrics
    update_global_metrics(coin)


def update_global_metrics(coin: str):
    """Update global metrics for a coin based on all clusters."""
    if coin not in EVENT_STORE:
        return

    clusters = EVENT_STORE[coin]["clusters"]

    if not clusters:
        EVENT_STORE[coin]["global_metrics"] = {
            "total_mentions": 0,
            "weighted_event_score": 0.0,
            "layer_a_weight": 0.0,
            "layer_b_weight": 0.0,
            "recency_decay_applied": True
        }
        return

    # Count total mentions
    total_mentions = sum(len(c["members"]) for c in clusters.values())

    # Calculate weighted event score
    layer_a_count = 0
    layer_b_count = 0
    total_event_score = 0.0

    for cluster_data in clusters.values():
        members = cluster_data["members"]
        layer_a_members = [m for m in members if m["source_type"] == "layer_a"]
        layer_b_members = [m for m in members if m["source_type"] == "layer_b"]

        layer_a_count += len(layer_a_members)
        layer_b_count += len(layer_b_members)

        # Weight by source type (layer_a: 0.6, layer_b: 0.4)
        cluster_score = cluster_data["event_score"]
        layer_a_weight = (len(layer_a_members) / len(members)) * 0.6 if members else 0
        layer_b_weight = (len(layer_b_members) / len(members)) * 0.4 if members else 0

        weighted_score = cluster_score * (layer_a_weight + layer_b_weight)
        total_event_score += weighted_score

    # Calculate layer contributions
    total_count = layer_a_count + layer_b_count
    layer_a_contribution = (layer_a_count / total_count) * 0.6 if total_count > 0 else 0
    layer_b_contribution = (layer_b_count / total_count) * 0.4 if total_count > 0 else 0

    EVENT_STORE[coin]["global_metrics"] = {
        "total_mentions": total_mentions,
        "weighted_event_score": float(total_event_score),
        "layer_a_weight": float(layer_a_contribution),
        "layer_b_weight": float(layer_b_contribution),
        "recency_decay_applied": True
    }

    EVENT_STORE[coin]["last_updated"] = datetime.utcnow()


def get_cluster_summary(coin: str) -> List[Dict[str, Any]]:
    """Get summary of all clusters for a coin."""
    if coin not in EVENT_STORE:
        return []

    clusters = EVENT_STORE[coin]["clusters"]
    summaries = []

    for cluster_id, cluster_data in clusters.items():
        members = cluster_data["members"]

        # Get top sources
        source_counts = defaultdict(int)
        for m in members:
            source_counts[m["source"]] += 1
        top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Calculate average credibility weight
        avg_credibility = sum(m["credibility_weight"] for m in members) / len(members) if members else 0

        summaries.append({
            "cluster_id": cluster_id,
            "event_score": cluster_data["event_score"],
            "mention_velocity": cluster_data["mention_velocity"],
            "member_count": len(members),
            "top_sources": [s[0] for s in top_sources],
            "credibility_weight_avg": float(avg_credibility)
        })

    return summaries


def get_raw_articles(coin: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get raw articles/posts from all clusters."""
    if coin not in EVENT_STORE:
        return []

    clusters = EVENT_STORE[coin]["clusters"]
    all_members = []

    for cluster_data in clusters.values():
        all_members.extend(cluster_data["members"])

    # Sort by timestamp (most recent first)
    all_members.sort(key=lambda x: x["timestamp"], reverse=True)

    # Return limited results without embeddings
    return [
        {
            "id": f"{m['platform_id']}_{hash(m['url'])}",  # Unique ID
            "title": m.get("title", ""),
            "summary": m.get("summary", ""),
            "text": m["text"],
            "full_content": m.get("full_content", m["text"]),
            "source_type": m["source_type"],
            "source": m["source"],
            "timestamp": m["timestamp"].isoformat(),
            "url": m["url"],
            "platform_id": m["platform_id"],
            "engagement_count": m["engagement_count"]
        }
        for m in all_members[:limit]
    ]


def get_article_by_id(coin: str, article_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific article by ID."""
    if coin not in EVENT_STORE:
        return None

    clusters = EVENT_STORE[coin]["clusters"]

    for cluster_data in clusters.values():
        for member in cluster_data["members"]:
            member_id = f"{member['platform_id']}_{hash(member['url'])}"
            if member_id == article_id:
                return {
                    "id": member_id,
                    "title": member.get("title", ""),
                    "summary": member.get("summary", ""),
                    "full_content": member.get("full_content", member["text"]),
                    "source_type": member["source_type"],
                    "source": member["source"],
                    "timestamp": member["timestamp"].isoformat(),
                    "url": member["url"],
                    "platform_id": member["platform_id"],
                    "engagement_count": member["engagement_count"]
                }

    return None

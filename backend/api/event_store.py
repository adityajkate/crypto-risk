"""In-memory event store for real-time sentiment tracking."""

import asyncio
import hashlib
import html
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlsplit, urlunsplit

STATE_FILE = Path(__file__).resolve().parents[1] / ".runtime" / "sentiment_state.json"
STATE_VERSION = 1
PERSIST_THROTTLE_SECONDS = 300.0  # 5 minutes

# Global in-memory state
EVENT_STORE: Dict[str, Dict[str, Any]] = {}

# asyncio queues for inter-worker communication
SCRAPE_QUEUE: asyncio.Queue = None
CLUSTER_QUEUE: asyncio.Queue = None

# Track which coins are actively being monitored
ACTIVE_COINS: Set[str] = set()

# Global cache for Fear & Greed and Google Trends
GLOBAL_SENTIMENT_CACHE: Dict[str, Any] = {
    "fear_greed": {"normalized": 0.0, "timestamp": None},
    "google_trends": {},
}

_LAST_PERSIST_TS = 0.0


def _empty_global_metrics(total_mentions: int = 0) -> Dict[str, Any]:
    return {
        "total_mentions": int(total_mentions),
        "sentiment_polarity": None,
        "sentiment_label": None,
        "unified_score": None,
        "layer_a_weight": 0.0,
        "layer_b_weight": 0.0,
        "bullish_percentage": None,
        "bearish_percentage": None,
        "neutral_percentage": None,
    }


def _normalize_url(url: str) -> str:
    if not url:
        return ""

    parsed = urlsplit(url.strip())
    if not parsed.scheme and not parsed.netloc:
        return url.strip()

    normalized_path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            parsed.query,
            "",
        )
    )


def _coerce_datetime(value: Any, default: Optional[datetime] = None) -> Optional[datetime]:
    if value is None:
        return default
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return default
    return default


def build_item_key(item: Dict[str, Any]) -> str:
    normalized_url = _normalize_url(item.get("url", ""))
    if normalized_url:
        return f"{item.get('platform_id', 'unknown')}::{normalized_url}"

    title = (item.get("title") or item.get("summary") or item.get("text") or "").strip().lower()
    return f"{item.get('platform_id', 'unknown')}::{title}"


def build_article_id(item: Dict[str, Any]) -> str:
    digest = hashlib.sha1(build_item_key(item).encode("utf-8")).hexdigest()[:16]
    return f"{item.get('platform_id', 'unknown')}_{digest}"


def _serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    serialized = dict(item)
    serialized["timestamp"] = (item.get("timestamp") or datetime.utcnow()).isoformat()
    return serialized


def _deserialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    deserialized = dict(item)
    deserialized["timestamp"] = _coerce_datetime(deserialized.get("timestamp"), datetime.utcnow())
    return deserialized


def _serialize_global_cache() -> Dict[str, Any]:
    fear_greed = GLOBAL_SENTIMENT_CACHE.get("fear_greed", {})
    timestamp = fear_greed.get("timestamp")
    return {
        "fear_greed": {
            "normalized": fear_greed.get("normalized"),
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else None,
        },
        "google_trends": GLOBAL_SENTIMENT_CACHE.get("google_trends", {}),
    }


def _clean_display_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_block_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value)).replace("\r\n", "\n")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _deserialize_global_cache(data: Dict[str, Any]) -> Dict[str, Any]:
    fear_greed = data.get("fear_greed", {})
    return {
        "fear_greed": {
            "normalized": fear_greed.get("normalized", 0.0),
            "timestamp": _coerce_datetime(fear_greed.get("timestamp")),
        },
        "google_trends": data.get("google_trends", {}),
    }


def initialize_queues():
    """Initialize asyncio queues on startup."""
    global SCRAPE_QUEUE, CLUSTER_QUEUE
    SCRAPE_QUEUE = asyncio.Queue(maxsize=500)  # Smaller = backpressure
    CLUSTER_QUEUE = asyncio.Queue(maxsize=200)


def initialize_coin(coin: str):
    """Initialize event store structure for a coin."""
    coin = coin.lower()
    if coin not in EVENT_STORE:
        EVENT_STORE[coin] = {
            "clusters": {},
            "pending_items": [],
            "known_item_keys": set(),
            "last_updated": datetime.utcnow(),
            "global_metrics": _empty_global_metrics(),
        }
        return

    EVENT_STORE[coin].setdefault("clusters", {})
    EVENT_STORE[coin].setdefault("pending_items", [])
    EVENT_STORE[coin].setdefault("known_item_keys", set())
    EVENT_STORE[coin].setdefault("last_updated", datetime.utcnow())
    EVENT_STORE[coin].setdefault("global_metrics", _empty_global_metrics())


def rebuild_known_item_keys(coin: str):
    """Rebuild known article keys from current state."""
    if coin not in EVENT_STORE:
        return

    EVENT_STORE[coin]["known_item_keys"] = {
        build_item_key(item) for item in get_all_items(coin)
    }


def remember_item(coin: str, item: Dict[str, Any]):
    """Track an article key so later duplicates can be ignored."""
    initialize_coin(coin)
    EVENT_STORE[coin]["known_item_keys"].add(build_item_key(item))


def is_item_known(coin: str, item: Dict[str, Any]) -> bool:
    """Check whether a coin already contains this article/post."""
    initialize_coin(coin)
    return build_item_key(item) in EVENT_STORE[coin]["known_item_keys"]


def add_coin_to_tracking(coin: str):
    """Add a coin to active tracking list."""
    coin = coin.lower()
    ACTIVE_COINS.add(coin)
    initialize_coin(coin)
    persist_state()


def get_active_coins() -> List[str]:
    """Get list of actively tracked coins."""
    return sorted(ACTIVE_COINS)


def get_coin_data(coin: str) -> Optional[Dict[str, Any]]:
    """Get event store data for a coin."""
    return EVENT_STORE.get(coin)


def get_all_items(coin: str) -> List[Dict[str, Any]]:
    """Get all known items for a coin, including unclustered pending articles."""
    if coin not in EVENT_STORE:
        return []

    items_by_key: Dict[str, Dict[str, Any]] = {}

    for cluster_data in EVENT_STORE[coin]["clusters"].values():
        for member in cluster_data.get("members", []):
            key = build_item_key(member)
            existing = items_by_key.get(key)
            if existing is None or member["timestamp"] > existing["timestamp"]:
                items_by_key[key] = member

    for pending_item in EVENT_STORE[coin]["pending_items"]:
        key = build_item_key(pending_item)
        existing = items_by_key.get(key)
        if existing is None or pending_item["timestamp"] > existing["timestamp"]:
            items_by_key[key] = pending_item

    return sorted(items_by_key.values(), key=lambda item: item["timestamp"], reverse=True)


def load_persisted_state():
    """Restore recently collected sentiment state from disk."""
    EVENT_STORE.clear()
    ACTIVE_COINS.clear()

    if not STATE_FILE.exists():
        return

    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return

    for coin in payload.get("active_coins", []):
        ACTIVE_COINS.add(str(coin).lower())

    GLOBAL_SENTIMENT_CACHE.clear()
    GLOBAL_SENTIMENT_CACHE.update(
        _deserialize_global_cache(payload.get("global_sentiment_cache", {}))
    )

    for coin, coin_payload in payload.get("coins", {}).items():
        clusters: Dict[int, Dict[str, Any]] = {}
        for cluster_id, cluster_data in coin_payload.get("clusters", {}).items():
            clusters[int(cluster_id)] = {
                "members": [
                    _deserialize_item(member)
                    for member in cluster_data.get("members", [])
                ],
                "sentiment": cluster_data.get("sentiment"),
                "unified_score": cluster_data.get("unified_score"),
                "mention_velocity": cluster_data.get("mention_velocity", 0.0),
            }

        EVENT_STORE[coin] = {
            "clusters": clusters,
            "pending_items": [
                _deserialize_item(item)
                for item in coin_payload.get("pending_items", [])
            ],
            "known_item_keys": set(coin_payload.get("known_item_keys", [])),
            "last_updated": _coerce_datetime(
                coin_payload.get("last_updated"),
                datetime.utcnow(),
            ),
            "global_metrics": coin_payload.get("global_metrics", _empty_global_metrics()),
        }
        initialize_coin(coin)
        prune_stale_data(coin, persist_changes=False)
        rebuild_known_item_keys(coin)


def persist_state(force: bool = False):
    """Persist recent event-store state to disk so reloads keep the feed intact."""
    global _LAST_PERSIST_TS

    now = time.monotonic()
    if not force and now - _LAST_PERSIST_TS < PERSIST_THROTTLE_SECONDS:
        return

    payload = {
        "version": STATE_VERSION,
        "saved_at": datetime.utcnow().isoformat(),
        "active_coins": sorted(ACTIVE_COINS),
        "global_sentiment_cache": _serialize_global_cache(),
        "coins": {},
    }

    for coin, coin_data in EVENT_STORE.items():
        payload["coins"][coin] = {
            "last_updated": coin_data.get("last_updated", datetime.utcnow()).isoformat(),
            "global_metrics": coin_data.get("global_metrics", _empty_global_metrics()),
            "pending_items": [
                _serialize_item(item)
                for item in coin_data.get("pending_items", [])
            ],
            "known_item_keys": sorted(list(coin_data.get("known_item_keys", set()))),
            "clusters": {
                str(cluster_id): {
                    "members": [
                        _serialize_item(member)
                        for member in cluster_data.get("members", [])
                    ],
                    "sentiment": cluster_data.get("sentiment"),
                    "unified_score": cluster_data.get("unified_score"),
                    "mention_velocity": cluster_data.get("mention_velocity", 0.0),
                }
                for cluster_id, cluster_data in coin_data.get("clusters", {}).items()
            },
        }

    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = STATE_FILE.with_suffix(".tmp")
        temp_file.write_text(json.dumps(payload), encoding="utf-8")
        temp_file.replace(STATE_FILE)
        _LAST_PERSIST_TS = now
    except Exception:
        return


def update_global_sentiment_cache(fear_greed: float = None, coin_trends: Dict[str, float] = None):
    """
    Update global sentiment cache with Fear & Greed and Google Trends data.

    Args:
        fear_greed: Normalized Fear & Greed value (-1 to 1)
        coin_trends: Dict mapping coin -> normalized trend value (0 to 1)
    """
    if fear_greed is not None:
        GLOBAL_SENTIMENT_CACHE["fear_greed"] = {
            "normalized": fear_greed,
            "timestamp": datetime.utcnow(),
        }

    if coin_trends is not None:
        GLOBAL_SENTIMENT_CACHE["google_trends"].update(coin_trends)

    persist_state()


def get_fear_greed_normalized() -> float:
    """Get cached Fear & Greed normalized value."""
    cache = GLOBAL_SENTIMENT_CACHE["fear_greed"]

    if cache["timestamp"]:
        age = (datetime.utcnow() - cache["timestamp"]).total_seconds()
        if age < 300:
            return cache["normalized"]

    return None


def get_google_trends_normalized(coin: str) -> float:
    """Get cached Google Trends normalized value for a coin."""
    return GLOBAL_SENTIMENT_CACHE["google_trends"].get(coin, None)


def calculate_mention_velocity(members: List[Dict[str, Any]]) -> float:
    """Calculate mention velocity (posts per hour)."""
    if not members:
        return 0.0

    time_window_hours = 3.0
    return len(members) / time_window_hours


def prune_stale_data(coin: str, max_age_minutes: int = 4320, persist_changes: bool = True):
    """
    Remove members older than max_age_minutes from all clusters and pending items.
    Called continuously by the clustering worker and during state restoration.
    Default: 4320 minutes = 3 days (72 hours)
    """
    if coin not in EVENT_STORE:
        return

    cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    coin_data = EVENT_STORE[coin]
    clusters_to_remove = []

    for cluster_id, cluster_data in coin_data["clusters"].items():
        cluster_data["members"] = [
            member for member in cluster_data.get("members", [])
            if member["timestamp"] > cutoff_time
        ]
        if not cluster_data["members"]:
            clusters_to_remove.append(cluster_id)

    for cluster_id in clusters_to_remove:
        del coin_data["clusters"][cluster_id]

    coin_data["pending_items"] = [
        item for item in coin_data.get("pending_items", [])
        if item["timestamp"] > cutoff_time
    ]

    rebuild_known_item_keys(coin)
    update_global_metrics(coin, persist_changes=persist_changes)


def update_global_metrics(coin: str, persist_changes: bool = True):
    """Update global metrics for a coin based on clustered and pending items."""
    if coin not in EVENT_STORE:
        return

    items = get_all_items(coin)
    clusters = EVENT_STORE[coin]["clusters"]

    if not items:
        EVENT_STORE[coin]["global_metrics"] = _empty_global_metrics()
        EVENT_STORE[coin]["last_updated"] = datetime.utcnow()
        if persist_changes:
            persist_state()
        return

    polarities = []
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0
    layer_a_count = 0
    layer_b_count = 0

    for item in items:
        sentiment = item.get("sentiment")
        if sentiment is not None:
            polarities.append(sentiment.get("polarity", 0.0))
            label = sentiment.get("label", "Neutral")
            if label == "Bullish":
                bullish_count += 1
            elif label == "Bearish":
                bearish_count += 1
            else:
                neutral_count += 1

        if item.get("source_type") == "layer_a":
            layer_a_count += 1
        else:
            layer_b_count += 1

    total_mentions = len(items)
    total_sentiment_count = bullish_count + bearish_count + neutral_count
    cluster_scores = [
        cluster_data.get("unified_score")
        for cluster_data in clusters.values()
        if cluster_data.get("unified_score") is not None
    ]

    if total_sentiment_count == 0:
        EVENT_STORE[coin]["global_metrics"] = _empty_global_metrics(total_mentions=total_mentions)
        EVENT_STORE[coin]["last_updated"] = datetime.utcnow()
        if persist_changes:
            persist_state()
        return

    avg_polarity = sum(polarities) / len(polarities) if polarities else None

    if bullish_count > bearish_count and bullish_count > neutral_count:
        sentiment_label = "Bullish"
    elif bearish_count > bullish_count and bearish_count > neutral_count:
        sentiment_label = "Bearish"
    else:
        sentiment_label = "Neutral"

    bullish_pct = (bullish_count / total_sentiment_count) * 100 if total_sentiment_count else 0.0
    bearish_pct = (bearish_count / total_sentiment_count) * 100 if total_sentiment_count else 0.0
    neutral_pct = (neutral_count / total_sentiment_count) * 100 if total_sentiment_count else 0.0

    total_layer_count = layer_a_count + layer_b_count
    layer_a_contribution = (layer_a_count / total_layer_count) * 0.6 if total_layer_count else 0.0
    layer_b_contribution = (layer_b_count / total_layer_count) * 0.4 if total_layer_count else 0.0

    EVENT_STORE[coin]["global_metrics"] = {
        "total_mentions": int(total_mentions),
        "sentiment_polarity": float(avg_polarity) if avg_polarity is not None else None,
        "sentiment_label": sentiment_label,
        "unified_score": (
            float(sum(cluster_scores) / len(cluster_scores))
            if cluster_scores
            else None
        ),
        "layer_a_weight": float(layer_a_contribution),
        "layer_b_weight": float(layer_b_contribution),
        "bullish_percentage": float(bullish_pct),
        "bearish_percentage": float(bearish_pct),
        "neutral_percentage": float(neutral_pct),
    }
    EVENT_STORE[coin]["last_updated"] = datetime.utcnow()

    if persist_changes:
        persist_state()


def get_cluster_summary(coin: str) -> List[Dict[str, Any]]:
    """Get summary of all clusters for a coin."""
    if coin not in EVENT_STORE:
        return []

    summaries = []

    for cluster_id, cluster_data in EVENT_STORE[coin]["clusters"].items():
        members = cluster_data.get("members", [])
        sentiment = cluster_data.get("sentiment")

        if sentiment is None:
            continue

        source_counts = defaultdict(int)
        for member in members:
            source_counts[member["source"]] += 1
        top_sources = sorted(source_counts.items(), key=lambda pair: pair[1], reverse=True)[:3]

        avg_credibility = (
            sum(member.get("credibility_weight", 0.0) for member in members) / len(members)
            if members
            else 0.0
        )

        unified_score = cluster_data.get("unified_score")
        summaries.append(
            {
                "cluster_id": int(cluster_id),
                "sentiment": sentiment,
                "unified_score": float(unified_score) if unified_score is not None else None,
                "mention_velocity": float(cluster_data.get("mention_velocity", 0.0)),
                "member_count": int(len(members)),
                "top_sources": [source for source, _ in top_sources],
                "credibility_weight_avg": float(avg_credibility),
            }
        )

    return summaries


def _format_article(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": build_article_id(item),
        "title": _clean_display_text(item.get("title", "")),
        "summary": _clean_display_text(item.get("summary", "")),
        "text": _clean_display_text(item.get("text", "")),
        "full_content": _clean_block_text(item.get("full_content", item.get("text", ""))),
        "source_type": item.get("source_type"),
        "source": _clean_display_text(item.get("source")),
        "timestamp": item.get("timestamp", datetime.utcnow()).isoformat(),
        "url": _clean_display_text(item.get("url", "")),
        "platform_id": item.get("platform_id"),
        "engagement_count": int(item.get("engagement_count", 0)),
        "image_url": _clean_display_text(item.get("image_url")) or None,
        "sentiment": item.get("sentiment"),
        "needs_full_fetch": item.get("needs_full_fetch", False),
    }


def get_raw_articles(coin: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get raw articles/posts from both clustered and pending items."""
    if coin not in EVENT_STORE:
        return []

    return [_format_article(item) for item in get_all_items(coin)[:limit]]


def get_article_by_id(coin: str, article_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific article by ID."""
    if coin not in EVENT_STORE:
        return None

    for item in get_all_items(coin):
        if build_article_id(item) == article_id:
            return _format_article(item)

    return None


def update_article_fields(coin: str, article_id: str, **fields: Any) -> bool:
    """Update an article in-place across pending and clustered items."""
    if coin not in EVENT_STORE:
        return False

    def _apply(items: List[Dict[str, Any]]) -> bool:
        updated = False
        for item in items:
            if build_article_id(item) != article_id:
                continue
            for key, value in fields.items():
                if value is not None:
                    item[key] = value
            updated = True
        return updated

    updated = _apply(EVENT_STORE[coin].get("pending_items", []))
    for cluster_data in EVENT_STORE[coin].get("clusters", {}).values():
        updated = _apply(cluster_data.get("members", [])) or updated

    if updated:
        persist_state()

    return updated

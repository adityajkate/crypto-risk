"""
Coin metadata mapping for sentiment tracking.

Maps CoinGecko IDs to sentiment keywords (name, symbol, aliases).
This ensures scrapers can match coins regardless of ID format.
"""

from typing import Dict, List, Optional, Tuple, Any

# Comprehensive coin metadata
# Format: coingecko_id -> {name, symbol, aliases}
COIN_METADATA: Dict[str, Dict[str, Any]] = {
    "bitcoin": {
        "name": "Bitcoin",
        "symbol": "BTC",
        "aliases": ["bitcoin", "btc"]
    },
    "ethereum": {
        "name": "Ethereum",
        "symbol": "ETH",
        "aliases": ["ethereum", "eth", "ether"]
    },
    "ripple": {
        "name": "XRP",
        "symbol": "XRP",
        "aliases": ["ripple", "xrp"]
    },
    "cardano": {
        "name": "Cardano",
        "symbol": "ADA",
        "aliases": ["cardano", "ada"]
    },
    "solana": {
        "name": "Solana",
        "symbol": "SOL",
        "aliases": ["solana", "sol"]
    },
    "polkadot": {
        "name": "Polkadot",
        "symbol": "DOT",
        "aliases": ["polkadot", "dot"]
    },
    "dogecoin": {
        "name": "Dogecoin",
        "symbol": "DOGE",
        "aliases": ["dogecoin", "doge"]
    },
    "avalanche-2": {
        "name": "Avalanche",
        "symbol": "AVAX",
        "aliases": ["avalanche", "avax"]
    },
    "chainlink": {
        "name": "Chainlink",
        "symbol": "LINK",
        "aliases": ["chainlink", "link"]
    },
    "polygon": {
        "name": "Polygon",
        "symbol": "MATIC",
        "aliases": ["polygon", "matic"]
    },
    "litecoin": {
        "name": "Litecoin",
        "symbol": "LTC",
        "aliases": ["litecoin", "ltc"]
    },
    "uniswap": {
        "name": "Uniswap",
        "symbol": "UNI",
        "aliases": ["uniswap", "uni"]
    },
    "binancecoin": {
        "name": "BNB",
        "symbol": "BNB",
        "aliases": ["binance coin", "bnb", "binance"]
    },
    "tron": {
        "name": "TRON",
        "symbol": "TRX",
        "aliases": ["tron", "trx"]
    },
    "stellar": {
        "name": "Stellar",
        "symbol": "XLM",
        "aliases": ["stellar", "xlm"]
    },
    "cosmos": {
        "name": "Cosmos",
        "symbol": "ATOM",
        "aliases": ["cosmos", "atom"]
    },
    "monero": {
        "name": "Monero",
        "symbol": "XMR",
        "aliases": ["monero", "xmr"]
    },
    "ethereum-classic": {
        "name": "Ethereum Classic",
        "symbol": "ETC",
        "aliases": ["ethereum classic", "etc"]
    },
    "tezos": {
        "name": "Tezos",
        "symbol": "XTZ",
        "aliases": ["tezos", "xtz"]
    },
    "algorand": {
        "name": "Algorand",
        "symbol": "ALGO",
        "aliases": ["algorand", "algo"]
    }
}


def _find_metadata_entry(coin_key: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Resolve metadata by CoinGecko ID, symbol, name, or alias.

    Returns:
        (coingecko_id, metadata) tuple if found, else (None, None)
    """
    normalized = coin_key.strip().lower()

    # Fast path: direct CoinGecko ID match
    direct = COIN_METADATA.get(normalized)
    if direct:
        return normalized, direct

    # Fallback: resolve by symbol, name, or aliases
    for coingecko_id, metadata in COIN_METADATA.items():
        symbol = str(metadata.get("symbol", "")).lower()
        name = str(metadata.get("name", "")).lower()
        aliases = [str(alias).lower() for alias in metadata.get("aliases", [])]

        if normalized == symbol or normalized == name or normalized in aliases:
            return coingecko_id, metadata

    return None, None


def get_sentiment_keywords(coingecko_id: str) -> List[str]:
    """
    Get all sentiment keywords for a coin.

    Returns a list of keywords to match in scraped content.
    Falls back to the coingecko_id if no metadata exists.
    """
    _, metadata = _find_metadata_entry(coingecko_id)

    if not metadata:
        # Fallback: use the ID itself, cleaned up
        cleaned_id = coingecko_id.replace("-", " ").replace("_", " ")
        return [coingecko_id, cleaned_id]

    # Return all possible keywords
    keywords = [
        metadata["name"].lower(),
        metadata["symbol"].lower(),
    ]
    keywords.extend([alias.lower() for alias in metadata["aliases"]])

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords


def get_sentiment_key(coingecko_id: str) -> str:
    """
    Get the primary sentiment tracking key for a coin.

    This is used as the storage key in the event store.
    Prefers symbol, falls back to name, then ID.
    """
    _, metadata = _find_metadata_entry(coingecko_id)

    if not metadata:
        # Fallback: use cleaned ID
        return coingecko_id.replace("-", "_").lower()

    # Prefer symbol (most common in discussions)
    return metadata["symbol"].lower()


def get_coin_display_name(coingecko_id: str) -> str:
    """Get the display name for a coin."""
    metadata = COIN_METADATA.get(coingecko_id)
    if not metadata:
        return coingecko_id.replace("-", " ").title()
    return metadata["name"]

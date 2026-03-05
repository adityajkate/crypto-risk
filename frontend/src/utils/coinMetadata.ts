/**
 * Coin metadata mapping for sentiment tracking.
 *
 * Maps CoinGecko IDs to sentiment keywords (name, symbol, aliases).
 * This ensures scrapers can match coins regardless of ID format.
 */

interface CoinMetadata {
  name: string;
  symbol: string;
  aliases: string[];
}

// Comprehensive coin metadata
// Format: coingecko_id -> {name, symbol, aliases}
export const COIN_METADATA: Record<string, CoinMetadata> = {
  "bitcoin": {
    name: "Bitcoin",
    symbol: "BTC",
    aliases: ["bitcoin", "btc", "₿"]
  },
  "ethereum": {
    name: "Ethereum",
    symbol: "ETH",
    aliases: ["ethereum", "eth", "ether"]
  },
  "ripple": {
    name: "XRP",
    symbol: "XRP",
    aliases: ["ripple", "xrp"]
  },
  "cardano": {
    name: "Cardano",
    symbol: "ADA",
    aliases: ["cardano", "ada"]
  },
  "solana": {
    name: "Solana",
    symbol: "SOL",
    aliases: ["solana", "sol"]
  },
  "polkadot": {
    name: "Polkadot",
    symbol: "DOT",
    aliases: ["polkadot", "dot"]
  },
  "dogecoin": {
    name: "Dogecoin",
    symbol: "DOGE",
    aliases: ["dogecoin", "doge"]
  },
  "avalanche-2": {
    name: "Avalanche",
    symbol: "AVAX",
    aliases: ["avalanche", "avax"]
  },
  "chainlink": {
    name: "Chainlink",
    symbol: "LINK",
    aliases: ["chainlink", "link"]
  },
  "polygon": {
    name: "Polygon",
    symbol: "MATIC",
    aliases: ["polygon", "matic"]
  },
  "litecoin": {
    name: "Litecoin",
    symbol: "LTC",
    aliases: ["litecoin", "ltc"]
  },
  "uniswap": {
    name: "Uniswap",
    symbol: "UNI",
    aliases: ["uniswap", "uni"]
  },
  "binancecoin": {
    name: "BNB",
    symbol: "BNB",
    aliases: ["binance coin", "bnb", "binance"]
  },
  "tron": {
    name: "TRON",
    symbol: "TRX",
    aliases: ["tron", "trx"]
  },
  "stellar": {
    name: "Stellar",
    symbol: "XLM",
    aliases: ["stellar", "xlm"]
  },
  "cosmos": {
    name: "Cosmos",
    symbol: "ATOM",
    aliases: ["cosmos", "atom"]
  },
  "monero": {
    name: "Monero",
    symbol: "XMR",
    aliases: ["monero", "xmr"]
  },
  "ethereum-classic": {
    name: "Ethereum Classic",
    symbol: "ETC",
    aliases: ["ethereum classic", "etc"]
  },
  "tezos": {
    name: "Tezos",
    symbol: "XTZ",
    aliases: ["tezos", "xtz"]
  },
  "algorand": {
    name: "Algorand",
    symbol: "ALGO",
    aliases: ["algorand", "algo"]
  }
};

/**
 * Get the primary sentiment tracking key for a coin.
 *
 * This is used as the storage key in the event store.
 * Prefers symbol, falls back to name, then ID.
 */
export function getSentimentKey(coingeckoId: string): string {
  const metadata = COIN_METADATA[coingeckoId.toLowerCase()];

  if (!metadata) {
    // Fallback: use cleaned ID
    return coingeckoId.replace(/-/g, '_').toLowerCase();
  }

  // Prefer symbol (most common in discussions)
  return metadata.symbol.toLowerCase();
}

/**
 * Get all sentiment keywords for a coin.
 *
 * Returns a list of keywords to match in scraped content.
 * Falls back to the coingecko_id if no metadata exists.
 */
export function getSentimentKeywords(coingeckoId: string): string[] {
  const metadata = COIN_METADATA[coingeckoId.toLowerCase()];

  if (!metadata) {
    // Fallback: use the ID itself, cleaned up
    const cleanedId = coingeckoId.replace(/-/g, ' ').replace(/_/g, ' ');
    return [coingeckoId, cleanedId];
  }

  // Return all possible keywords
  const keywords = [
    metadata.name.toLowerCase(),
    metadata.symbol.toLowerCase(),
    ...metadata.aliases.map(alias => alias.toLowerCase())
  ];

  // Remove duplicates while preserving order
  return Array.from(new Set(keywords));
}

/**
 * Get the display name for a coin.
 */
export function getCoinDisplayName(coingeckoId: string): string {
  const metadata = COIN_METADATA[coingeckoId.toLowerCase()];
  if (!metadata) {
    return coingeckoId.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
  return metadata.name;
}

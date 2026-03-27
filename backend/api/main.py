"""FastAPI application for Crypto Risk Lens."""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import html
import re
import pandas as pd

from backend.api.config import settings
from backend.api.coingecko_realtime import CoinGeckoRealtimeClient
from backend.api.fear_greed_client import FearGreedClient
from backend.api.google_trends_client import GoogleTrendsClient
from backend.models.predictor import RiskPredictor
from backend.api.event_store import (
    initialize_queues,
    SCRAPE_QUEUE,
    CLUSTER_QUEUE,
    get_coin_data,
    get_cluster_summary,
    get_raw_articles,
    get_article_by_id,
    add_coin_to_tracking,
    get_active_coins,
    load_persisted_state,
    persist_state,
    update_article_fields,
    update_global_sentiment_cache
)
from backend.scrapers.layer_a import LayerAScraper
from backend.scrapers.layer_b import LayerBScraper
from backend.workers.sentiment_worker import SentimentWorker
from backend.workers.clustering_worker import ClusteringWorker
import asyncio


# Initialize FastAPI app
app = FastAPI(
    title="Crypto Risk Lens API",
    description="Real-time cryptocurrency risk analysis with ML predictions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize clients
coingecko_client = None
fear_greed_client = None
google_trends_client = None
risk_predictor = None

# Background workers
layer_a_scraper = None
layer_b_scraper = None
sentiment_worker = None
clustering_worker = None

# Background tasks
background_tasks = []


def _clean_article_text(value: Optional[str]) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _needs_article_refresh(article: dict) -> bool:
    full_content = _clean_article_text(article.get("full_content"))
    summary = _clean_article_text(article.get("summary"))

    if not full_content:
        return True
    if len(full_content) < 500:
        return True
    if summary and full_content.lower() == summary.lower():
        return True
    return False


@app.on_event("startup")
async def startup_event():
    """Initialize clients and start background workers."""
    global coingecko_client, fear_greed_client, google_trends_client, risk_predictor
    global layer_a_scraper, layer_b_scraper, sentiment_worker, clustering_worker
    global background_tasks

    # Initialize queues
    initialize_queues()
    load_persisted_state()

    # Initialize CoinGecko client
    coingecko_client = CoinGeckoRealtimeClient(
        api_key=settings.coingecko_api_key,
        rate_limit_delay=settings.rate_limit_delay
    )

    # Initialize Fear & Greed client
    fear_greed_client = FearGreedClient()

    # Initialize Google Trends client
    google_trends_client = GoogleTrendsClient()

    # Initialize risk predictor
    risk_predictor = RiskPredictor(artifacts_dir=settings.artifacts_dir)

    # Initialize scrapers and workers
    layer_a_scraper = LayerAScraper(SCRAPE_QUEUE)
    layer_b_scraper = LayerBScraper(SCRAPE_QUEUE)
    sentiment_worker = SentimentWorker(SCRAPE_QUEUE, CLUSTER_QUEUE)
    clustering_worker = ClusteringWorker(CLUSTER_QUEUE)

    # Start background tasks with dynamic coin tracking - optimized intervals
    background_tasks.append(asyncio.create_task(layer_a_scraper.run_dynamic(interval_minutes=15)))
    background_tasks.append(asyncio.create_task(layer_b_scraper.run_dynamic(interval_minutes=20)))
    background_tasks.append(asyncio.create_task(sentiment_worker.run()))
    background_tasks.append(asyncio.create_task(clustering_worker.run()))
    background_tasks.append(asyncio.create_task(update_global_sentiment_loop()))

    print("API initialized successfully with CryptoBERT sentiment analysis")


async def update_global_sentiment_loop():
    """Background task to update Fear & Greed and Google Trends cache."""
    while True:
        try:
            # Update Fear & Greed Index (every 5 minutes)
            if fear_greed_client:
                fng_data = await fear_greed_client.get_current_index()
                update_global_sentiment_cache(fear_greed=fng_data["normalized"])
                print(f"[Global Sentiment] Fear & Greed: {fng_data['value']} ({fng_data['value_classification']})")

            # Update Google Trends for active coins (every 10 minutes)
            active_coins = get_active_coins()
            if active_coins and google_trends_client:
                trends_data = {}
                for coin in active_coins[:5]:  # Limit to 5 coins to avoid rate limiting
                    try:
                        from core.coin_metadata import get_sentiment_keywords
                        keywords = get_sentiment_keywords(coin)
                        if keywords:
                            trend = await google_trends_client.get_search_interest(keywords[0])
                            trends_data[coin] = trend["normalized"]
                            print(f"[Google Trends] {coin}: {trend['current_interest']} ({trend['trend']})")
                    except Exception as e:
                        print(f"[Google Trends] Error for {coin}: {e}")

                if trends_data:
                    update_global_sentiment_cache(coin_trends=trends_data)

            # Wait 5 minutes before next update
            await asyncio.sleep(300)

        except Exception as e:
            print(f"[Global Sentiment] Error: {e}")
            await asyncio.sleep(60)


@app.on_event("shutdown")
async def shutdown_event():
    """Close clients and stop background workers."""
    # Stop workers
    if layer_a_scraper:
        await layer_a_scraper.stop()
    if layer_b_scraper:
        await layer_b_scraper.stop()
    if sentiment_worker:
        await sentiment_worker.stop()
    if clustering_worker:
        await clustering_worker.stop()

    # Cancel background tasks
    for task in background_tasks:
        task.cancel()

    persist_state(force=True)

    # Close clients
    if coingecko_client:
        await coingecko_client.close()
    if fear_greed_client:
        await fear_greed_client.close()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Crypto Risk Lens API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "coin_analysis": "/api/v1/coin/{coin_id}/analysis",
            "coin_price": "/api/v1/coin/{coin_id}/price",
            "trending": "/api/v1/trending",
            "global_market": "/api/v1/global",
            "sentiment": "/api/v1/sentiment/{currency}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "coingecko_configured": settings.coingecko_api_key is not None,
        "models_loaded": risk_predictor is not None
    }


@app.get("/api/v1/coin/{coin_id}/price")
async def get_coin_price(coin_id: str):
    """Get current price and market data for a coin."""
    try:
        price_data = await coingecko_client.get_coin_price(coin_id)
        return {
            "success": True,
            "data": price_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/coin/{coin_id}/analysis")
async def get_coin_analysis(
    coin_id: str,
    days: int = Query(default=30, ge=7, le=365, description="Days of historical data")
):
    """
    Get comprehensive risk analysis for a coin.

    Includes:
    - Current price and market data
    - Risk assessment (low/medium/high)
    - Volatility forecast
    - Market cluster
    - Market regime
    """
    try:
        # Get current price data
        price_data = await coingecko_client.get_coin_price(coin_id)

        # Get OHLC data for analysis
        ohlc_df = await coingecko_client.get_coin_ohlc(coin_id, days=days)

        # Add volume column (approximate if not available)
        if "volume" not in ohlc_df.columns:
            ohlc_df["volume"] = price_data.get("total_volume", 0)

        # Get ML predictions
        analysis = risk_predictor.get_comprehensive_analysis(ohlc_df)

        return {
            "success": True,
            "data": {
                "coin_id": coin_id,
                "current_price": price_data,
                "risk_analysis": analysis,
                "data_points": len(ohlc_df),
                "analysis_period_days": days
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/coin/{coin_id}/ohlc")
async def get_coin_ohlc_data(
    coin_id: str,
    days: int = Query(default=7, ge=1, le=365, description="Days of historical data")
):
    """
    Get historical OHLC (Open, High, Low, Close) data for a coin.

    Returns real historical price data from CoinGecko.
    """
    try:
        # Get OHLC data from CoinGecko
        ohlc_df = await coingecko_client.get_coin_ohlc(coin_id, days=days)

        # Convert DataFrame to list of dicts
        ohlc_data = []
        for idx, row in ohlc_df.iterrows():
            ohlc_data.append({
                "timestamp": int(row["timestamp"].timestamp() * 1000),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"])
            })

        return {
            "success": True,
            "data": {
                "coin_id": coin_id,
                "ohlc": ohlc_data,
                "days": days,
                "data_points": len(ohlc_data)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/coin/{coin_id}/indicators")
async def get_coin_indicators(
    coin_id: str,
    days: int = Query(default=30, ge=7, le=365, description="Days of historical data")
):
    """
    Get technical indicators for a coin.

    Returns TA-Lib indicators including:
    - RSI, MACD, Bollinger Bands
    - Stochastic RSI, ADX, CCI
    - Williams %R, MFI, ROC
    - Momentum, TRIX, Ultimate Oscillator
    - Aroon Oscillator, Balance of Power
    """
    try:
        # Get OHLC data
        ohlcv_df = await coingecko_client.get_coin_ohlc(coin_id, days=days)

        # Add volume column (approximate if not available)
        price_data = await coingecko_client.get_coin_price(coin_id)
        if "volume" not in ohlcv_df.columns:
            ohlcv_df["volume"] = price_data.get("total_volume", 0)

        # Calculate features
        features_df = risk_predictor.feature_engine.transform(ohlcv_df)

        if len(features_df) == 0:
            raise HTTPException(status_code=400, detail="Insufficient data for indicators")

        # Get latest indicators
        latest = features_df.iloc[-1]

        indicators = {
            "momentum_indicators": {
                "rsi_14": float(latest["rsi_14"]),
                "stoch_rsi": float(latest["stoch_rsi"]),
                "macd": float(latest["macd"]),
                "macd_signal": float(latest["macd_signal"]),
                "macd_hist": float(latest["macd_hist"]),
                "momentum": float(latest["momentum"]),
                "roc": float(latest["roc"])
            },
            "trend_indicators": {
                "adx": float(latest["adx"]),
                "aroon_osc": float(latest["aroon_osc"]),
                "cci": float(latest["cci"]),
                "trix": float(latest["trix"])
            },
            "volatility_indicators": {
                "atr_14": float(latest["atr_14"]),
                "bb_width": float(latest["bb_width"]),
                "bb_upper": float(latest["bb_upper"]),
                "bb_lower": float(latest["bb_lower"]),
                "volatility_7d": float(latest["volatility_7d"]),
                "volatility_30d": float(latest["volatility_30d"])
            },
            "volume_indicators": {
                "obv": float(latest["obv"]),
                "mfi": float(latest["mfi"]),
                "volume_sma_ratio": float(latest["volume_sma_ratio"])
            },
            "oscillators": {
                "willr": float(latest["willr"]),
                "ultosc": float(latest["ultosc"]),
                "bop": float(latest["bop"])
            },
            "price_action": {
                "drawdown": float(latest["drawdown"]),
                "max_drawdown_30d": float(latest["max_drawdown_30d"]),
                "price_sma50_ratio": float(latest["price_sma50_ratio"]),
                "returns_1d": float(latest["returns_1d"])
            }
        }

        return {
            "success": True,
            "data": {
                "coin_id": coin_id,
                "indicators": indicators,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/coin/{coin_id}/risk")
async def get_coin_risk(coin_id: str, days: int = Query(default=30, ge=7, le=365)):
    """Get risk assessment only for a coin."""
    try:
        ohlc_df = await coingecko_client.get_coin_ohlc(coin_id, days=days)

        # Add approximate volume
        price_data = await coingecko_client.get_coin_price(coin_id)
        if "volume" not in ohlc_df.columns:
            ohlc_df["volume"] = price_data.get("total_volume", 0)

        risk_assessment = risk_predictor.predict_risk(ohlc_df)

        return {
            "success": True,
            "data": {
                "coin_id": coin_id,
                "risk_assessment": risk_assessment
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/coins/search")
async def search_coins(query: str = Query(..., min_length=1)):
    """Search for coins by name or symbol with relevance sorting."""
    try:
        results = await coingecko_client.search_coins(query)

        # Format results to match frontend expectations
        coins = results.get("coins", [])
        query_lower = query.lower()

        # Score each coin for relevance
        scored_coins = []
        for coin in coins:
            name = coin.get("name", "").lower()
            symbol = coin.get("symbol", "").lower()
            coin_id = coin.get("id", "").lower()

            # Calculate relevance score (higher is better)
            score = 0

            # Exact symbol match (highest priority)
            if symbol == query_lower:
                score += 10000
            elif symbol.startswith(query_lower):
                score += 500
            elif query_lower in symbol:
                score += 100

            # Exact name match
            if name == query_lower:
                score += 8000
            elif name.startswith(query_lower):
                score += 400
            elif query_lower in name:
                score += 80

            # ID match
            if coin_id == query_lower:
                score += 6000
            elif coin_id.startswith(query_lower):
                score += 300
            elif query_lower in coin_id:
                score += 60

            # Boost popular coins significantly (if they have market_cap_rank)
            rank = coin.get("market_cap_rank")
            if rank:
                # Top 10 coins get huge boost, then decreasing
                if rank <= 10:
                    score += 1000
                elif rank <= 50:
                    score += 500
                elif rank <= 100:
                    score += 200
                else:
                    score += max(0, 100 - rank)

            scored_coins.append((score, coin))

        # Sort by score (descending) and take top 8
        scored_coins.sort(key=lambda x: x[0], reverse=True)
        top_coins = [coin for score, coin in scored_coins[:8]]

        formatted_coins = [
            {
                "id": coin.get("id"),
                "name": coin.get("name"),
                "symbol": coin.get("symbol", "").upper(),
                "thumb": coin.get("thumb"),
                "large": coin.get("large")
            }
            for coin in top_coins
        ]

        return {
            "success": True,
            "data": {
                "coins": formatted_coins,
                "count": len(formatted_coins)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/trending")
async def get_trending_coins():
    """Get trending coins with risk analysis."""
    try:
        trending = await coingecko_client.get_trending_coins()

        return {
            "success": True,
            "data": {
                "trending_coins": trending,
                "count": len(trending)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/global")
async def get_global_market():
    """Get global cryptocurrency market data."""
    try:
        global_data = await coingecko_client.get_global_market_data()

        return {
            "success": True,
            "data": global_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/coins/top")
async def get_top_coins(limit: int = Query(20, ge=1, le=100)):
    """Get top coins by market cap with full market data.

    Args:
        limit: Number of coins to return (1-100, default 20)

    Returns:
        List of top coins with price, market cap, volume, and 24h change data
    """
    try:
        data = await coingecko_client._rate_limited_request(
            "coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": False,
                "price_change_percentage": "24h"
            }
        )

        # Format the response
        coins = []
        for coin in data:
            coins.append({
                "id": coin["id"],
                "symbol": coin["symbol"].upper(),
                "name": coin["name"],
                "image": coin.get("image"),
                "current_price": coin.get("current_price", 0),
                "market_cap": coin.get("market_cap", 0),
                "market_cap_rank": coin.get("market_cap_rank", 0),
                "total_volume": coin.get("total_volume", 0),
                "price_change_24h": coin.get("price_change_24h", 0),
                "price_change_percentage_24h": coin.get("price_change_percentage_24h", 0),
                "circulating_supply": coin.get("circulating_supply", 0),
                "total_supply": coin.get("total_supply"),
                "ath": coin.get("ath", 0),
                "atl": coin.get("atl", 0),
                "last_updated": coin.get("last_updated")
            })

        return {
            "success": True,
            "data": {
                "coins": coins,
                "count": len(coins)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/batch/analysis")
async def get_batch_analysis(
    coin_ids: str = Query(..., description="Comma-separated coin IDs (e.g., bitcoin,ethereum,ripple)"),
    days: int = Query(default=30, ge=7, le=365)
):
    """Get risk analysis for multiple coins at once."""
    try:
        coin_list = [c.strip() for c in coin_ids.split(",")]

        if len(coin_list) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 coins per request")

        results = []
        for coin_id in coin_list:
            try:
                # Get OHLC data
                ohlc_df = await coingecko_client.get_coin_ohlc(coin_id, days=days)
                price_data = await coingecko_client.get_coin_price(coin_id)

                if "volume" not in ohlc_df.columns:
                    ohlc_df["volume"] = price_data.get("total_volume", 0)

                # Get risk analysis
                analysis = risk_predictor.get_comprehensive_analysis(ohlc_df)

                results.append({
                    "coin_id": coin_id,
                    "current_price": price_data.get("current_price"),
                    "risk_level": analysis["risk_assessment"].get("risk_label"),
                    "confidence": analysis["risk_assessment"].get("confidence"),
                    "full_analysis": analysis
                })
            except Exception as e:
                results.append({
                    "coin_id": coin_id,
                    "error": str(e)
                })

        return {
            "success": True,
            "data": {
                "results": results,
                "count": len(results)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentiment/{currency}")
async def get_sentiment(currency: str):
    """
    Get real-time sentiment analysis for a cryptocurrency.

    Returns actual sentiment (Bullish/Bearish/Neutral) with unified scoring.

    Args:
        currency: CoinGecko ID (e.g., 'bitcoin', 'avalanche-2')
    """
    try:
        # Import coin metadata utilities
        from core.coin_metadata import get_sentiment_key

        # Convert CoinGecko ID to sentiment key
        sentiment_key = get_sentiment_key(currency.lower())

        # Add coin to tracking if not already tracked
        add_coin_to_tracking(sentiment_key)

        # Get data from event store
        coin_data = get_coin_data(sentiment_key)

        if not coin_data:
            # Coin was just added, return empty state
            return {
                "success": True,
                "data": {
                    "coin": sentiment_key,
                    "global_metrics": {
                        "total_mentions": 0,
                        "sentiment_polarity": None,
                        "sentiment_label": None,
                        "unified_score": None,
                        "layer_a_weight": 0.0,
                        "layer_b_weight": 0.0,
                        "bullish_percentage": None,
                        "bearish_percentage": None,
                        "neutral_percentage": None
                    },
                    "clusters": [],
                    "last_updated": datetime.utcnow().isoformat(),
                    "data_window_hours": 72,
                    "status": "collecting_data"
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        # Get cluster summaries
        clusters = get_cluster_summary(sentiment_key)

        return {
            "success": True,
            "data": {
                "coin": sentiment_key,
                "global_metrics": coin_data["global_metrics"],
                "clusters": clusters,
                "last_updated": coin_data["last_updated"].isoformat(),
                "data_window_hours": 72,
                "status": "active"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentiment/{currency}/raw")
async def get_sentiment_raw(
    currency: str,
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of articles to return"),
    offset: int = Query(default=0, ge=0, description="Number of articles to skip for pagination")
):
    """
    Get raw articles/posts for a cryptocurrency.

    Returns the actual scraped content from the last 3 days (72 hours).

    Args:
        currency: CoinGecko ID (e.g., 'bitcoin', 'avalanche-2')
        limit: Maximum number of articles to return (1-500)
        offset: Number of articles to skip for pagination
    """
    try:
        # Import coin metadata utilities
        from core.coin_metadata import get_sentiment_key

        # Convert CoinGecko ID to sentiment key
        sentiment_key = get_sentiment_key(currency.lower())

        # Add coin to tracking if not already tracked
        add_coin_to_tracking(sentiment_key)

        # Get raw articles
        all_articles = get_raw_articles(sentiment_key, limit=limit + offset)

        # Apply pagination
        articles = all_articles[offset:offset + limit]

        return {
            "success": True,
            "data": {
                "coin": sentiment_key,
                "articles": articles,
                "count": len(articles),
                "total": len(all_articles),
                "offset": offset,
                "limit": limit,
                "data_window_hours": 72,
                "status": "collecting_data" if len(articles) == 0 else "active"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentiment/{currency}/article/{article_id}")
async def get_article_detail(currency: str, article_id: str):
    """
    Get full article content by ID.

    Returns complete article content for in-app display (no redirect needed).
    Automatically fetches full content for articles that only have summaries.
    """
    try:
        # Convert CoinGecko ID to sentiment storage key
        from core.coin_metadata import get_sentiment_key
        coin = get_sentiment_key(currency.lower())

        # Get article by ID
        article = get_article_by_id(coin, article_id)

        if not article:
            raise HTTPException(
                status_code=404,
                detail=f"Article not found for {currency}"
            )

        # Check if article needs full content fetch
        should_fetch = (
            layer_a_scraper and
            article.get("url") and
            (_needs_article_refresh(article) or article.get("needs_full_fetch", False))
        )

        if should_fetch:
            try:
                refreshed_content, refreshed_image = await layer_a_scraper.fetch_full_article(article["url"])
                refreshed_content = _clean_article_text(refreshed_content)

                old_content = _clean_article_text(article.get("full_content", ""))
                
                # Update if we got better content
                should_update_content = False
                if not old_content:
                    should_update_content = True
                elif len(old_content) < 300 and len(refreshed_content) > 300:
                    should_update_content = True
                elif len(refreshed_content) > len(old_content) * 0.8 and refreshed_content != old_content:
                    should_update_content = True

                if should_update_content:
                    article["full_content"] = refreshed_content
                    if refreshed_image and not article.get("image_url"):
                        article["image_url"] = refreshed_image

                    # Update in store
                    update_article_fields(
                        coin,
                        article_id,
                        full_content=article["full_content"],
                        image_url=article.get("image_url"),
                        needs_full_fetch=False  # Mark as fetched
                    )
                else:
                    update_article_fields(coin, article_id, needs_full_fetch=False)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to fetch full article: {e}")
                update_article_fields(coin, article_id, needs_full_fetch=False)

        return {
            "success": True,
            "data": article,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentiment/{currency}/history")
async def get_sentiment_history(
    currency: str,
    days: int = Query(default=3, ge=1, le=7, description="Days of history (1-7)"),
    limit: int = Query(default=100, ge=1, le=500, description="Max articles per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset")
):
    """
    Get historical articles for a cryptocurrency (up to 7 days).

    Returns articles with complete details including sentiment analysis.
    Full article content is fetched on-demand via article detail endpoint.

    Args:
        currency: CoinGecko ID (e.g., 'bitcoin', 'avalanche-2')
        days: Number of days of history (1-7, default 3)
        limit: Maximum articles per page (default 100)
        offset: Pagination offset (default 0)
    """
    try:
        from core.coin_metadata import get_sentiment_key
        from datetime import timedelta

        sentiment_key = get_sentiment_key(currency.lower())
        add_coin_to_tracking(sentiment_key)

        # Get all articles
        all_articles = get_raw_articles(sentiment_key, limit=5000)

        # Filter by date range
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        filtered_articles = [
            article for article in all_articles
            if datetime.fromisoformat(article["timestamp"]) > cutoff_time
        ]

        # Apply pagination
        total_count = len(filtered_articles)
        paginated_articles = filtered_articles[offset:offset + limit]

        return {
            "success": True,
            "data": {
                "coin": sentiment_key,
                "articles": paginated_articles,
                "count": len(paginated_articles),
                "total_count": total_count,
                "days": days,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total_count,
                "status": "collecting_data" if total_count == 0 else "active"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentiment/{currency}/summary")
async def get_sentiment_summary(currency: str):
    """
    Generate a comprehensive summary of all news for a cryptocurrency.

    Analyzes all articles from the last 180 minutes and provides:
    - Overall sentiment trend
    - Key topics and themes
    - Major events mentioned
    - Risk indicators

    Args:
        currency: CoinGecko ID (e.g., 'bitcoin', 'avalanche-2')
    """
    try:
        # Import coin metadata utilities
        from core.coin_metadata import get_sentiment_key
        from backend.services.nlp_summarizer import get_summarizer

        # Convert CoinGecko ID to sentiment key
        sentiment_key = get_sentiment_key(currency.lower())

        # Get all articles
        articles = get_raw_articles(sentiment_key, limit=500)

        if not articles:
            return {
                "success": True,
                "data": {
                    "coin": sentiment_key,
                    "summary": f"No recent news data available for {sentiment_key}. Please wait 5-15 minutes for articles to be collected.",
                    "article_count": 0,
                    "time_window_hours": 72,
                "key_insights": [],
                "sentiment": "Neutral",
                "confidence": 0,
                "price_impact": "None",
                "reasoning": "No data available",
                "risk_factors": [],
                "summary_source": "no_data",
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Get coin data for metrics
        coin_data = get_coin_data(sentiment_key)

        # Analyze articles
        total_articles = len(articles)
        layer_a_count = sum(1 for a in articles if a.get("source_type") == "layer_a")
        layer_b_count = sum(1 for a in articles if a.get("source_type") == "layer_b")

        # Use NLP to generate intelligent summary
        summarizer = get_summarizer()
        nlp_result = await summarizer.summarize_articles_async(articles, sentiment_key)

        # Get sentiment from coin data (for additional context)
        sentiment_label = None
        unified_score = None
        bullish_percentage = None
        bearish_percentage = None
        neutral_percentage = None

        if coin_data:
            metrics = coin_data.get("global_metrics", {})
            sentiment_label = metrics.get("sentiment_label")
            unified_score = metrics.get("unified_score")
            bullish_percentage = metrics.get("bullish_percentage")
            bearish_percentage = metrics.get("bearish_percentage")
            neutral_percentage = metrics.get("neutral_percentage")

        # Use NLP sentiment (more dynamic and based on recent articles)
        # Keep CryptoBERT sentiment in sentiment_label for reference

        return {
            "success": True,
            "data": {
                "coin": sentiment_key,
                "summary": nlp_result.get("summary"),
                "article_count": total_articles,
                "layer_a_count": layer_a_count,
                "layer_b_count": layer_b_count,
                "time_window_hours": 72,
                "key_insights": nlp_result.get("key_insights", []),
                "sentiment": nlp_result.get("sentiment", "Neutral"),
                "confidence": nlp_result.get("confidence", 0),
                "price_impact": nlp_result.get("price_impact", "None"),
                "reasoning": nlp_result.get("reasoning", ""),
                "risk_factors": nlp_result.get("risk_factors", []),
                "summary_source": nlp_result.get("summary_source", "nlp"),
                "sentiment_label": sentiment_label,
                "unified_score": unified_score,
                "bullish_percentage": bullish_percentage,
                "bearish_percentage": bearish_percentage,
                "neutral_percentage": neutral_percentage,
                "recent_articles": articles[:5]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/proxy/image")
async def proxy_image(url: str):
    """
    Proxy images to avoid CORS issues.

    This endpoint fetches images from external sources and returns them,
    allowing the frontend to display images that might otherwise be blocked by CORS.
    """
    try:
        from urllib.parse import urlparse
        import httpx

        # Validate URL to prevent SSRF
        parsed = urlparse(url)

        # Only allow HTTPS and specific trusted domains
        if parsed.scheme != 'https':
            raise HTTPException(status_code=400, detail="Only HTTPS URLs are allowed")

        # Whitelist of allowed domains for image proxying
        allowed_domains = [
            'assets.coingecko.com',
            'coin-images.coingecko.com',
        ]

        if not any(parsed.netloc.endswith(domain) for domain in allowed_domains):
            raise HTTPException(status_code=403, detail="Domain not allowed")

        # Prevent access to private IP ranges
        import ipaddress
        try:
            # Resolve hostname to IP
            import socket
            ip = socket.gethostbyname(parsed.netloc)
            ip_obj = ipaddress.ip_address(ip)

            # Block private, loopback, and link-local addresses
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                raise HTTPException(status_code=403, detail="Private IP addresses not allowed")
        except socket.gaierror:
            raise HTTPException(status_code=400, detail="Invalid hostname")

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False, max_redirects=0) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()

            # Validate content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="URL does not point to an image")

            from fastapi.responses import Response
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'Access-Control-Allow-Origin': 'http://localhost:3000'
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch image: {str(e)}")


@app.get("/api/v1/fear-greed")
async def get_fear_greed_index():
    """
    Get current Crypto Fear & Greed Index.

    Returns:
        Current index value (0-100) and classification
    """
    try:
        if not fear_greed_client:
            raise HTTPException(status_code=503, detail="Fear & Greed client not initialized")

        data = await fear_greed_client.get_current_index()

        return {
            "success": True,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/fear-greed/historical")
async def get_fear_greed_historical(days: int = Query(default=7, ge=1, le=30)):
    """
    Get historical Fear & Greed Index data.

    Args:
        days: Number of days to fetch (1-30)
    """
    try:
        if not fear_greed_client:
            raise HTTPException(status_code=503, detail="Fear & Greed client not initialized")

        data = await fear_greed_client.get_historical(limit=days)

        return {
            "success": True,
            "data": {
                "historical": data,
                "count": len(data)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )

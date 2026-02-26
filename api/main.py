"""FastAPI application for Crypto Risk Lens."""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import pandas as pd

from api.config import settings
from api.coingecko_realtime import CoinGeckoRealtimeClient
from api.cryptopanic_client import CryptoPanicClient
from api.predictor import RiskPredictor
from api.event_store import (
    initialize_queues,
    SCRAPE_QUEUE,
    CLUSTER_QUEUE,
    get_coin_data,
    get_cluster_summary,
    get_raw_articles,
    get_article_by_id,
    add_coin_to_tracking,
    get_active_coins
)
from api.scrapers.layer_a import LayerAScraper
from api.scrapers.layer_b import LayerBScraper
from api.workers.embedding_worker import EmbeddingWorker
from api.workers.clustering_worker import ClusteringWorker
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
coingecko_client = None
cryptopanic_client = None
risk_predictor = None

# Background workers
layer_a_scraper = None
layer_b_scraper = None
embedding_worker = None
clustering_worker = None

# Background tasks
background_tasks = []


@app.on_event("startup")
async def startup_event():
    """Initialize clients and start background workers."""
    global coingecko_client, cryptopanic_client, risk_predictor
    global layer_a_scraper, layer_b_scraper, embedding_worker, clustering_worker
    global background_tasks

    # Initialize queues
    initialize_queues()

    # Initialize CoinGecko client
    coingecko_client = CoinGeckoRealtimeClient(
        api_key=settings.coingecko_api_key,
        rate_limit_delay=settings.rate_limit_delay
    )

    # Initialize CryptoPanic client (only if API key is provided)
    if settings.cryptopanic_api_key:
        cryptopanic_client = CryptoPanicClient(
            api_key=settings.cryptopanic_api_key,
            rate_limit_delay=settings.rate_limit_delay
        )

    # Initialize risk predictor
    risk_predictor = RiskPredictor(artifacts_dir=settings.artifacts_dir)

    # Initialize scrapers and workers
    layer_a_scraper = LayerAScraper(SCRAPE_QUEUE)
    layer_b_scraper = LayerBScraper(SCRAPE_QUEUE)
    embedding_worker = EmbeddingWorker(SCRAPE_QUEUE, CLUSTER_QUEUE)
    clustering_worker = ClusteringWorker(CLUSTER_QUEUE)

    # Start background tasks with dynamic coin tracking
    # Scrapers will track coins dynamically as users search for them
    background_tasks.append(asyncio.create_task(layer_a_scraper.run_dynamic(interval_minutes=15)))
    background_tasks.append(asyncio.create_task(layer_b_scraper.run_dynamic(interval_minutes=5)))
    background_tasks.append(asyncio.create_task(embedding_worker.run()))
    background_tasks.append(asyncio.create_task(clustering_worker.run()))

    print("API initialized successfully with dynamic sentiment tracking")


@app.on_event("shutdown")
async def shutdown_event():
    """Close clients and stop background workers."""
    # Stop workers
    if layer_a_scraper:
        await layer_a_scraper.stop()
    if layer_b_scraper:
        await layer_b_scraper.stop()
    if embedding_worker:
        await embedding_worker.stop()
    if clustering_worker:
        await clustering_worker.stop()

    # Cancel background tasks
    for task in background_tasks:
        task.cancel()

    # Close clients
    if coingecko_client:
        await coingecko_client.close()
    if cryptopanic_client:
        await cryptopanic_client.close()


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
            "news": "/api/v1/news",
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
        "cryptopanic_configured": settings.cryptopanic_api_key is not None,
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
async def get_coin_ohlc(
    coin_id: str,
    days: int = Query(default=7, ge=1, le=365, description="Days of historical data")
):
    """
    Get historical OHLC (Open, High, Low, Close) data for a coin.

    Returns candlestick data for charting.
    """
    try:
        ohlc_df = await coingecko_client.get_coin_ohlc(coin_id, days=days)

        # Convert DataFrame to list of dicts
        ohlc_data = []
        for idx, row in ohlc_df.iterrows():
            ohlc_data.append({
                "timestamp": int(idx.timestamp() * 1000),
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


@app.get("/api/v1/news")
async def get_news(
    currencies: Optional[str] = Query(None, description="Comma-separated coin symbols (e.g., BTC,ETH)"),
    filter_type: str = Query(default="hot", description="Filter: hot, rising, bullish, bearish, important"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get cryptocurrency news from CryptoPanic."""
    if not cryptopanic_client:
        raise HTTPException(status_code=503, detail="CryptoPanic API key not configured")

    try:
        posts = await cryptopanic_client.get_posts(
            currencies=currencies,
            filter_type=filter_type,
            limit=limit
        )

        return {
            "success": True,
            "data": {
                "posts": posts,
                "count": len(posts),
                "filter": filter_type
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sentiment/{currency}")
async def get_sentiment(currency: str):
    """
    Get real-time sentiment analysis for a cryptocurrency.

    Returns quantitative event metrics from in-memory event store.
    """
    try:
        coin = currency.lower()

        # Add coin to tracking if not already tracked
        add_coin_to_tracking(coin)

        # Get data from event store
        coin_data = get_coin_data(coin)

        if not coin_data:
            # Coin was just added, return empty state
            return {
                "success": True,
                "data": {
                    "coin": coin,
                    "global_metrics": {
                        "total_mentions": 0,
                        "weighted_event_score": 0.0,
                        "layer_a_weight": 0.0,
                        "layer_b_weight": 0.0,
                        "recency_decay_applied": True
                    },
                    "clusters": [],
                    "last_updated": datetime.utcnow().isoformat(),
                    "data_window_minutes": 180,
                    "status": "collecting_data"
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        # Get cluster summaries
        clusters = get_cluster_summary(coin)

        return {
            "success": True,
            "data": {
                "coin": coin,
                "global_metrics": coin_data["global_metrics"],
                "clusters": clusters,
                "last_updated": coin_data["last_updated"].isoformat(),
                "data_window_minutes": 180,
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
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of articles to return")
):
    """
    Get raw articles/posts for a cryptocurrency.

    Returns the actual scraped content from the last 180 minutes.
    """
    try:
        coin = currency.lower()

        # Add coin to tracking if not already tracked
        add_coin_to_tracking(coin)

        # Get raw articles
        articles = get_raw_articles(coin, limit=limit)

        return {
            "success": True,
            "data": {
                "coin": coin,
                "articles": articles,
                "count": len(articles),
                "data_window_minutes": 180,
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
    """
    try:
        coin = currency.lower()

        # Get article by ID
        article = get_article_by_id(coin, article_id)

        if not article:
            raise HTTPException(
                status_code=404,
                detail=f"Article not found for {currency}"
            )

        return {
            "success": True,
            "data": article,
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
    """
    try:
        coin = currency.lower()

        # Get all articles
        articles = get_raw_articles(coin, limit=500)

        if not articles:
            return {
                "success": True,
                "data": {
                    "coin": coin,
                    "summary": f"No recent news data available for {coin}. Please wait 5-15 minutes for articles to be collected.",
                    "article_count": 0,
                    "time_window_minutes": 180,
                    "key_topics": [],
                    "sentiment": "neutral"
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        # Get coin data for metrics
        coin_data = get_coin_data(coin)

        # Analyze articles
        total_articles = len(articles)
        layer_a_count = sum(1 for a in articles if a.get("source_type") == "layer_a")
        layer_b_count = sum(1 for a in articles if a.get("source_type") == "layer_b")

        # Extract key topics (most common words in titles)
        from collections import Counter
        import re

        all_titles = " ".join([a.get("title", "") for a in articles])
        # Remove common words and extract meaningful terms
        words = re.findall(r'\b[A-Za-z]{4,}\b', all_titles.lower())
        common_words = {'bitcoin', 'ethereum', 'crypto', 'cryptocurrency', 'coin', 'price', 'market', 'trading', coin.lower()}
        filtered_words = [w for w in words if w not in common_words]
        word_counts = Counter(filtered_words)
        key_topics = [word for word, count in word_counts.most_common(10)]

        # Generate summary text
        summary_parts = []
        summary_parts.append(f"Analysis of {total_articles} articles about {coin.upper()} from the last 3 hours.")
        summary_parts.append(f"Sources: {layer_a_count} authoritative news articles and {layer_b_count} social media posts.")

        if coin_data:
            metrics = coin_data.get("global_metrics", {})
            event_score = metrics.get("weighted_event_score", 0)

            if event_score > 0.7:
                summary_parts.append(f"⚠️ HIGH ACTIVITY: Event score of {event_score:.2f} indicates significant market attention.")
            elif event_score > 0.4:
                summary_parts.append(f"📊 MODERATE ACTIVITY: Event score of {event_score:.2f} shows normal market interest.")
            else:
                summary_parts.append(f"📉 LOW ACTIVITY: Event score of {event_score:.2f} indicates quiet market conditions.")

        if key_topics:
            summary_parts.append(f"Key topics: {', '.join(key_topics[:5])}.")

        # Determine overall sentiment based on event score and article count
        sentiment = "neutral"
        if coin_data:
            event_score = coin_data.get("global_metrics", {}).get("weighted_event_score", 0)
            if event_score > 0.6:
                sentiment = "bullish"
            elif event_score < 0.3:
                sentiment = "bearish"

        summary_text = " ".join(summary_parts)

        return {
            "success": True,
            "data": {
                "coin": coin,
                "summary": summary_text,
                "article_count": total_articles,
                "layer_a_count": layer_a_count,
                "layer_b_count": layer_b_count,
                "time_window_minutes": 180,
                "key_topics": key_topics[:10],
                "sentiment": sentiment,
                "event_score": coin_data.get("global_metrics", {}).get("weighted_event_score", 0) if coin_data else 0,
                "recent_articles": articles[:5]  # Include 5 most recent articles
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
        import httpx
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()

            from fastapi.responses import Response
            return Response(
                content=response.content,
                media_type=response.headers.get('content-type', 'image/jpeg'),
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'Access-Control-Allow-Origin': '*'
                }
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch image: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )

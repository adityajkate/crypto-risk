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


@app.on_event("startup")
async def startup_event():
    """Initialize clients on startup."""
    global coingecko_client, cryptopanic_client, risk_predictor

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

    print("API initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close clients on shutdown."""
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
    """Get sentiment analysis for a specific cryptocurrency."""
    if not cryptopanic_client:
        raise HTTPException(status_code=503, detail="CryptoPanic API key not configured")

    try:
        sentiment = await cryptopanic_client.get_sentiment_for_coin(currency.upper())

        return {
            "success": True,
            "data": sentiment,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )

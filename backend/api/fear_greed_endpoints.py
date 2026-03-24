"""New API endpoint for Fear & Greed Index."""

# Add this endpoint to main.py after the sentiment endpoints

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

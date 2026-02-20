"""
Startup script for Crypto Risk Lens API.

Usage:
    python run_api.py
"""
import uvicorn
from api.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Crypto Risk Lens API")
    print("=" * 60)
    print(f"Host: {settings.api_host}")
    print(f"Port: {settings.api_port}")
    print(f"CoinGecko API: {'✓ Configured' if settings.coingecko_api_key else '✗ Not configured (using free tier)'}")
    print(f"CryptoPanic API: {'✓ Configured' if settings.cryptopanic_api_key else '✗ Not configured'}")
    print("=" * 60)
    print(f"\nAPI will be available at: http://{settings.api_host}:{settings.api_port}")
    print(f"API docs: http://{settings.api_host}:{settings.api_port}/docs")
    print("\n")

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )

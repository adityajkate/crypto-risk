"""
Startup script for Crypto Risk Lens API.

Usage:
    python run_api.py
"""

import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from backend.api.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Crypto Risk Lens API")
    print("=" * 60)
    print(f"Host: {settings.api_host}")
    print(f"Port: {settings.api_port}")
    print(
        f"CoinGecko API: {'Configured' if settings.coingecko_api_key else 'Not configured (using free tier)'}"
    )

    google_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    if google_key:
        print(f"Google Gemini API: Configured ({google_key[:20]}...)")
    else:
        print(
            "Google Gemini API: NOT CONFIGURED - summary endpoint will report unavailable"
        )

    print("=" * 60)
    print(f"\nAPI will be available at: http://{settings.api_host}:{settings.api_port}")
    print(f"API docs: http://{settings.api_host}:{settings.api_port}/docs")
    print("\n")

    uvicorn.run(
        "backend.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )

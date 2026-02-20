import pytest
import httpx
from shared.coingecko_client import CoinGeckoClient

@pytest.mark.asyncio
async def test_fetch_top_coins():
    client = CoinGeckoClient()
    coins = await client.fetch_top_coins(limit=5)
    assert len(coins) == 5
    assert all('id' in c for c in coins)
    assert all('symbol' in c for c in coins)
    await client.close()

@pytest.mark.asyncio
async def test_fetch_coin_history():
    client = CoinGeckoClient()
    df = await client.fetch_coin_history('bitcoin', days=30)
    assert not df.empty
    assert 'timestamp' in df.columns
    assert 'price' in df.columns
    assert 'volume' in df.columns
    await client.close()

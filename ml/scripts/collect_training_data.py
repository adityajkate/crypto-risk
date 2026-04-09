import pandas as pd
from pathlib import Path
import yfinance as yf
from datetime import datetime, timedelta


class TrainingDataCollector:
    # Map CoinGecko IDs to Yahoo Finance tikers
    CRYPTO_TICKERS = {
        "bitcoin": "BTC-USD",
        "ethereum": "ETH-USD",
        "tether": "USDT-USD",
        "binancecoin": "BNB-USD",
        "solana": "SOL-USD",
        "usd-coin": "USDC-USD",
        "ripple": "XRP-USD",
        "dogecoin": "DOGE-USD",
        "cardano": "ADA-USD",
        "tron": "TRX-USD",
        "avalanche-2": "AVAX-USD",
        "chainlink": "LINK-USD",
        "shiba-inu": "SHIB-USD",
        "polkadot": "DOT-USD",
        "bitcoin-cash": "BCH-USD",
        "litecoin": "LTC-USD",
        "uniswap": "UNI-USD",
        "stellar": "XLM-USD",
        "monero": "XMR-USD",
        "hedera-hashgraph": "HBAR-USD",
        "aave": "AAVE-USD",
        "the-open-network": "TON11419-USD",
        "sui": "SUI20947-USD",
        "pepe": "PEPE24478-USD",
        "zcash": "ZEC-USD",
        "dai": "DAI-USD",
        "crypto-com-chain": "CRO-USD",
        "mantle": "MNT27075-USD",
        "okb": "OKB-USD",
        "leo-token": "LEO-USD",
        "bittensor": "TAO22974-USD",
        "pax-gold": "PAXG-USD",
        "tether-gold": "XAUT-USD",
        "sky": "SKY-USD",
        "ethena-usde": "USDE29470-USD",
        "paypal-usd": "PYUSD-USD",
        "bitget-token": "BGB-USD",
        "hyperliquid": "HYPE-USD",
        # Stablecoins and tokens that may not have Yahoo tickers
        "usds": None,
        "hashnote-usyc": None,
        "global-dollar": None,
        "blackrock-usd-institutional-digital-liquidity-fund": None,
        "figure-heloc": None,
        "canton-network": None,
        "falcon-finance": None,
        "rain": None,
        "pi-network": None,
        "aster-2": None,
        "memecore": None,
        "usd1-wlfi": None,
        "whitebit": None,
        "world-liberty-financial": None,
    }

    def __init__(
        self, output_dir: Path = None, days: int = 1825
    ):  # 5 years = 1825 days
        self.output_dir = output_dir or Path(__file__).parent.parent / "data" / "raw"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.days = days

    def collect(self) -> None:
        """Fetch and save data for crypto coins using yfinance."""
        print(f"Fetching {len(self.CRYPTO_TICKERS)} coins using yfinance...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days)

        success_count = 0
        skipped_count = 0

        for i, (coin_id, ticker) in enumerate(self.CRYPTO_TICKERS.items(), 1):
            if ticker is None:
                print(
                    f"[{i}/{len(self.CRYPTO_TICKERS)}] Skipping {coin_id} (no Yahoo ticker)"
                )
                skipped_count += 1
                continue

            print(f"[{i}/{len(self.CRYPTO_TICKERS)}] Fetching {coin_id} ({ticker})...")
            try:
                # Download data from yfinance
                df = yf.download(ticker, start=start_date, end=end_date, progress=False)

                if df.empty:
                    print(f"  ✗ No data returned")
                    continue

                # Flatten multi-index columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # Reset index to get timestamp as column
                df = df.reset_index()

                # Rename columns to match our format
                df = df.rename(
                    columns={
                        "Date": "timestamp",
                        "Open": "open",
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Volume": "volume",
                    }
                )

                # Select only needed columns
                df = df[["timestamp", "open", "high", "low", "close", "volume"]]

                # Ensure all data is numeric and clean
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

                # Drop any rows with NaN values
                df = df.dropna()

                if len(df) == 0:
                    print(f"  ✗ No valid data after cleaning")
                    continue

                # Save to CSV
                output_path = self.output_dir / f"{coin_id}_history.csv"
                df.to_csv(output_path, index=False)
                print(f"  ✓ Saved {len(df)} rows to {output_path.name}")
                success_count += 1

            except Exception as e:
                print(f"  ✗ Error: {e}")

        print(f"\n{'='*60}")
        print(f"Completed: {success_count} fetched, {skipped_count} skipped")
        print(f"{'='*60}")


def main():
    collector = TrainingDataCollector()
    collector.collect()


if __name__ == "__main__":
    main()

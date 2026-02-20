import pandas as pd
import numpy as np
import talib

class MarketFeatureEngine:
    """Engineer technical indicators from OHLCV data."""

    REQUIRED_COLS = ["timestamp", "open", "high", "low", "close", "volume"]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform OHLCV DataFrame with technical indicators.
        Drops rows with NaN values.
        """
        df = df.copy()
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Returns
        df["returns_1d"] = df["close"].pct_change() * 100
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

        # Volatility
        df["volatility_7d"] = df["log_returns"].rolling(7).std()
        df["volatility_30d"] = df["log_returns"].rolling(30).std()

        # RSI
        df["rsi_14"] = talib.RSI(df["close"], timeperiod=14)

        # MACD
        macd, macd_signal, macd_hist = talib.MACD(
            df["close"], fastperiod=12, slowperiod=26, signalperiod=9
        )
        df["macd"] = macd
        df["macd_signal"] = macd_signal
        df["macd_hist"] = macd_hist

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            df["close"], timeperiod=20, nbdevup=2, nbdevdn=2
        )
        df["bb_upper"] = bb_upper
        df["bb_lower"] = bb_lower
        df["bb_width"] = (bb_upper - bb_lower) / bb_middle

        # ATR
        df["atr_14"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)

        # OBV
        df["obv"] = talib.OBV(df["close"], df["volume"])

        # Volume ratio
        df["volume_sma_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        # Drawdown
        rolling_max = df["close"].expanding().max()
        df["drawdown"] = (df["close"] / rolling_max - 1) * 100

        # Price to SMA ratios
        df["price_sma50_ratio"] = df["close"] / df["close"].rolling(50).mean()
        df["price_sma200_ratio"] = df["close"] / df["close"].rolling(200).mean()

        # Drop NaN rows
        df = df.dropna()

        return df

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

        # Drawdown features (PRIORITY 4: Enhanced)
        # Use rolling max with reasonable window for daily data
        rolling_max = df["close"].rolling(window=90, min_periods=30).max()
        df["drawdown"] = (df["close"] / rolling_max - 1) * 100

        # Max drawdown over 30 days
        df["max_drawdown_30d"] = df["drawdown"].rolling(30, min_periods=10).min()

        # Drawdown duration (days in drawdown)
        in_drawdown = df["drawdown"] < -1  # More than 1% below peak
        df["drawdown_duration"] = in_drawdown.groupby((~in_drawdown).cumsum()).cumsum()

        # Recovery ratio (how far recovered from max drawdown)
        df["recovery_ratio"] = df["drawdown"] / df["max_drawdown_30d"].replace(0, -1)

        # Interaction: drawdown * volatility (structural instability)
        df["drawdown_vol_interaction"] = df["drawdown"].abs() * df["volatility_30d"]

        # Price to SMA ratios (reduced windows)
        df["price_sma50_ratio"] = df["close"] / df["close"].rolling(50, min_periods=20).mean()
        df["price_sma200_ratio"] = df["close"] / df["close"].rolling(100, min_periods=50).mean()

        # Advanced Momentum Indicators
        # Stochastic RSI
        df["stoch_rsi"] = talib.STOCHRSI(df["close"], timeperiod=14)[0]

        # ADX (Average Directional Index) - Trend Strength
        df["adx"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)

        # CCI (Commodity Channel Index)
        df["cci"] = talib.CCI(df["high"], df["low"], df["close"], timeperiod=20)

        # Williams %R
        df["willr"] = talib.WILLR(df["high"], df["low"], df["close"], timeperiod=14)

        # Money Flow Index (MFI)
        df["mfi"] = talib.MFI(df["high"], df["low"], df["close"], df["volume"], timeperiod=14)

        # Rate of Change (ROC)
        df["roc"] = talib.ROC(df["close"], timeperiod=10)

        # Momentum
        df["momentum"] = talib.MOM(df["close"], timeperiod=10)

        # Triple Exponential Moving Average (TRIX)
        df["trix"] = talib.TRIX(df["close"], timeperiod=15)

        # Ultimate Oscillator
        df["ultosc"] = talib.ULTOSC(df["high"], df["low"], df["close"])

        # Aroon Oscillator
        df["aroon_osc"] = talib.AROONOSC(df["high"], df["low"], timeperiod=14)

        # Balance of Power
        df["bop"] = talib.BOP(df["open"], df["high"], df["low"], df["close"])

        # NEW: Add more predictive features
        # Price momentum and acceleration
        df["price_momentum_5d"] = df["close"].pct_change(5) * 100
        df["price_momentum_10d"] = df["close"].pct_change(10) * 100
        df["price_acceleration"] = df["returns_1d"].diff()  # Rate of change of returns

        # Volume trends (leading indicator)
        df["volume_trend_5d"] = df["volume"].rolling(5).mean() / df["volume"].rolling(20).mean()
        df["volume_spike"] = df["volume"] / df["volume"].rolling(20).mean()

        # Volatility trends (predict volatility spikes)
        df["volatility_trend"] = df["volatility_7d"] / df["volatility_30d"]
        df["volatility_acceleration"] = df["volatility_7d"].diff()

        # Price extremes (predict reversals)
        df["distance_from_high"] = (df["close"] / df["high"].rolling(30).max() - 1) * 100
        df["distance_from_low"] = (df["close"] / df["low"].rolling(30).min() - 1) * 100

        # Trend strength
        df["trend_strength"] = abs(df["close"].rolling(20).mean() - df["close"].rolling(50).mean()) / df["close"]

        # RSI divergence (leading indicator)
        df["rsi_change"] = df["rsi_14"].diff()
        df["price_rsi_divergence"] = df["returns_1d"] - df["rsi_change"]

        # Regime Detection Features (PRIORITY 6)
        # FIX: Use rolling quantiles with smaller window
        # Compute thresholds on rolling 90-day window
        vol_threshold_high = df["volatility_7d"].rolling(window=90, min_periods=30).quantile(0.75)
        vol_threshold_low = df["volatility_7d"].rolling(window=90, min_periods=30).quantile(0.25)

        df["regime"] = 1  # Default to moderate/transition
        df.loc[df["volatility_7d"] <= vol_threshold_low, "regime"] = 0  # Low vol stable
        df.loc[(df["volatility_7d"] > vol_threshold_high) & (df["returns_1d"] < 0), "regime"] = 2  # High vol crisis

        # Regime interaction features
        df["regime_volatility_interaction"] = df["regime"] * df["volatility_30d"]
        df["regime_drawdown_interaction"] = df["regime"] * df["drawdown"].abs()

        # Drop NaN rows
        df = df.dropna()

        return df

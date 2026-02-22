"""Model inference service for risk predictions."""
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.feature_engine import MarketFeatureEngine


class RiskPredictor:
    """Load trained models and make risk predictions."""

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.feature_engine = MarketFeatureEngine()
        self._load_models()

    def _load_models(self):
        """Load all trained models from artifacts directory."""
        try:
            # Load risk classifier
            self.risk_scaler = joblib.load(self.artifacts_dir / "scaler.joblib")
            self.risk_model = joblib.load(self.artifacts_dir / "risk_rf.joblib")  # Use Random Forest

            # Load Winsorization parameters
            try:
                winsorization = joblib.load(self.artifacts_dir / "winsorization_params.joblib")
                self.percentile_1 = pd.Series(winsorization["percentile_1"])
                self.percentile_99 = pd.Series(winsorization["percentile_99"])
            except FileNotFoundError:
                print("Warning: Winsorization parameters not found, skipping outlier clipping")
                self.percentile_1 = None
                self.percentile_99 = None

            # Load volatility regression
            self.volatility_model = joblib.load(self.artifacts_dir / "volatility_linreg.joblib")
            self.volatility_qreg_10 = joblib.load(self.artifacts_dir / "volatility_qreg_10.joblib")
            self.volatility_qreg_50 = joblib.load(self.artifacts_dir / "volatility_qreg_50.joblib")
            self.volatility_qreg_90 = joblib.load(self.artifacts_dir / "volatility_qreg_90.joblib")

            # Load clustering
            self.cluster_scaler = joblib.load(self.artifacts_dir / "cluster_scaler.joblib")
            self.kmeans_model = joblib.load(self.artifacts_dir / "kmeans_market.joblib")

            # Load regime detection
            self.regime_hmm = joblib.load(self.artifacts_dir / "regime_hmm.joblib")
            self.regime_names = joblib.load(self.artifacts_dir / "regime_names.joblib")

            # Load PCA
            self.pca_scaler = joblib.load(self.artifacts_dir / "pca_scaler.joblib")
            self.pca_model = joblib.load(self.artifacts_dir / "pca_transformer.joblib")

            # Load feature lists
            self.risk_features = [
                # Returns and Volatility
                "returns_1d", "log_returns", "volatility_7d", "volatility_30d",
                # Classic Indicators
                "rsi_14", "macd", "macd_signal", "macd_hist",
                "bb_width", "atr_14", "obv", "volume_sma_ratio",
                "drawdown", "price_sma50_ratio", "price_sma200_ratio",
                # Enhanced Drawdown Features
                "max_drawdown_30d", "drawdown_duration", "recovery_ratio", "drawdown_vol_interaction",
                # Advanced Momentum Indicators
                "stoch_rsi", "adx", "cci", "willr", "mfi",
                "roc", "momentum", "trix", "ultosc", "aroon_osc", "bop",
                # Regime Features
                "regime_volatility_interaction", "regime_drawdown_interaction"
            ]

            self.cluster_features = [
                "volatility_7d", "volatility_30d", "returns_1d",
                "volume_sma_ratio", "rsi_14", "bb_width", "drawdown"
            ]

            print("All models loaded successfully")

        except Exception as e:
            print(f"Error loading models: {e}")
            raise

    def prepare_ohlcv_data(self, price_history: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert price history to OHLCV DataFrame.

        Args:
            price_history: List of dicts with 'timestamp', 'open', 'high', 'low', 'close', 'volume'
        """
        df = pd.DataFrame(price_history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    def predict_risk(self, ohlcv_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict risk level for a coin based on OHLCV data.

        Returns:
            Dict with risk_level (0=low, 1=medium, 2=high), probability, and features
        """
        # Generate features
        features_df = self.feature_engine.transform(ohlcv_data)

        if len(features_df) == 0:
            return {"error": "Insufficient data for prediction"}

        # Use most recent data point
        latest = features_df.iloc[-1]
        X = latest[self.risk_features].values.reshape(1, -1)
        X = np.nan_to_num(X, 0)

        # Apply Winsorization if parameters are available
        if self.percentile_1 is not None and self.percentile_99 is not None:
            X_df = pd.DataFrame(X, columns=self.risk_features)
            for col in self.risk_features:
                if col in self.percentile_1.index:
                    X_df[col] = X_df[col].clip(
                        lower=self.percentile_1[col],
                        upper=self.percentile_99[col]
                    )
            X = X_df.values

        # Scale and predict
        X_scaled = self.risk_scaler.transform(X)
        risk_level = int(self.risk_model.predict(X_scaled)[0])
        risk_proba = self.risk_model.predict_proba(X_scaled)[0]

        risk_labels = {0: "low", 1: "medium", 2: "high"}

        # PRIORITY 2: Check confidence threshold
        max_confidence = float(risk_proba.max())
        confidence_margin = risk_proba[np.argsort(risk_proba)[-1]] - risk_proba[np.argsort(risk_proba)[-2]]
        is_uncertain = max_confidence < 0.65 or confidence_margin < 0.10  # Add margin check

        # Strict taxonomy: risk_label must be "low", "medium", or "high" only
        risk_label_output = risk_labels[risk_level]

        # Warning message for uncertain predictions
        warning = None
        if is_uncertain:
            if confidence_margin < 0.10:
                warning = f"Low confidence margin ({confidence_margin:.3f}) - top 2 classes too close"
            else:
                warning = "Low confidence prediction - treat as weak signal"

        return {
            "risk_level": risk_level,
            "risk_label": risk_label_output,
            "probabilities": {
                "low": float(risk_proba[0]),
                "medium": float(risk_proba[1]),
                "high": float(risk_proba[2])
            },
            "confidence": max_confidence,
            "confidence_margin": float(confidence_margin),
            "is_uncertain": bool(is_uncertain),
            "warning": warning,
            "features": {
                "volatility_30d": float(latest["volatility_30d"]),
                "rsi_14": float(latest["rsi_14"]),
                "drawdown": float(latest["drawdown"]),
                "returns_1d": float(latest["returns_1d"])
            }
        }

    def predict_volatility(self, ohlcv_data: pd.DataFrame) -> Dict[str, Any]:
        """Predict future volatility with confidence intervals."""
        features_df = self.feature_engine.transform(ohlcv_data)

        if len(features_df) == 0:
            return {"error": "Insufficient data for prediction"}

        latest = features_df.iloc[-1]

        # Prepare features for volatility prediction
        vol_features = [
            "volatility_7d", "volatility_30d", "rsi_14", "atr_14",
            "bb_width", "volume_sma_ratio", "drawdown", "price_sma50_ratio", "macd_hist"
        ]
        X = latest[vol_features].values.reshape(1, -1)
        X = np.nan_to_num(X, 0)

        # Predict with linear regression
        predicted_vol = float(self.volatility_model.predict(X)[0])

        # Get quantile predictions for confidence intervals
        # Manually add constant column for quantile regression models
        X_const = np.column_stack([np.ones((X.shape[0], 1)), X])
        vol_10 = float(self.volatility_qreg_10.predict(X_const)[0])
        vol_50 = float(self.volatility_qreg_50.predict(X_const)[0])
        vol_90 = float(self.volatility_qreg_90.predict(X_const)[0])

        return {
            "predicted_volatility_7d": predicted_vol,
            "confidence_intervals": {
                "lower_10": vol_10,
                "median_50": vol_50,
                "upper_90": vol_90
            },
            "current_volatility_7d": float(latest["volatility_7d"]),
            "current_volatility_30d": float(latest["volatility_30d"])
        }

    def predict_market_cluster(self, ohlcv_data: pd.DataFrame) -> Dict[str, Any]:
        """Identify which market cluster the coin belongs to."""
        features_df = self.feature_engine.transform(ohlcv_data)

        if len(features_df) == 0:
            return {"error": "Insufficient data for prediction"}

        latest = features_df.iloc[-1]
        X = latest[self.cluster_features].values.reshape(1, -1)
        X = np.nan_to_num(X, 0)

        # Scale and predict cluster
        X_scaled = self.cluster_scaler.transform(X)
        cluster = int(self.kmeans_model.predict(X_scaled)[0])

        return {
            "cluster": cluster,
            "cluster_name": f"market_regime_{cluster}",
            "features": {
                "volatility_7d": float(latest["volatility_7d"]),
                "volatility_30d": float(latest["volatility_30d"]),
                "returns_1d": float(latest["returns_1d"])
            }
        }

    def predict_regime(self, ohlcv_data: pd.DataFrame) -> Dict[str, Any]:
        """Detect current market regime using HMM."""
        features_df = self.feature_engine.transform(ohlcv_data)

        if len(features_df) < 10:
            return {"error": "Insufficient data for regime detection (need at least 10 points)"}

        # Use recent history for regime detection
        recent = features_df.tail(30)
        X = recent[["log_returns", "volatility_7d"]].values
        X = np.nan_to_num(X, 0)

        # Predict regime
        regime_state = int(self.regime_hmm.predict(X)[-1])
        regime_name = self.regime_names.get(regime_state, "unknown")

        return {
            "regime_state": regime_state,
            "regime_name": regime_name,
            "description": self._get_regime_description(regime_name)
        }

    def _get_regime_description(self, regime_name: str) -> str:
        """Get human-readable description of regime."""
        descriptions = {
            "low_vol_stable": "Low volatility, stable market conditions",
            "moderate_transition": "Moderate volatility, transitional phase",
            "high_vol_crisis": "High volatility, crisis or extreme market conditions"
        }
        return descriptions.get(regime_name, "Unknown market regime")

    def get_comprehensive_analysis(self, ohlcv_data: pd.DataFrame) -> Dict[str, Any]:
        """Get complete risk analysis with probability-regime blending."""
        # Get base predictions
        volatility_forecast = self.predict_volatility(ohlcv_data)
        market_cluster = self.predict_market_cluster(ohlcv_data)
        market_regime = self.predict_regime(ohlcv_data)

        # Generate features for risk prediction
        features_df = self.feature_engine.transform(ohlcv_data)
        if len(features_df) == 0:
            return {"error": "Insufficient data for prediction"}

        latest = features_df.iloc[-1]
        X = latest[self.risk_features].values.reshape(1, -1)
        X = np.nan_to_num(X, 0)

        # Apply Winsorization if parameters are available
        if self.percentile_1 is not None and self.percentile_99 is not None:
            X_df = pd.DataFrame(X, columns=self.risk_features)
            for col in self.risk_features:
                if col in self.percentile_1.index:
                    X_df[col] = X_df[col].clip(
                        lower=self.percentile_1[col],
                        upper=self.percentile_99[col]
                    )
            X = X_df.values

        # Scale and get base probabilities
        X_scaled = self.risk_scaler.transform(X)
        risk_proba = self.risk_model.predict_proba(X_scaled)[0].copy()

        # FIX #1: Probability-regime blending (replace deterministic overrides)
        regime_name = market_regime.get("regime_name", "unknown")

        # Apply regime-based probability adjustments
        if regime_name == "high_vol_crisis":
            # Penalize low risk probability in crisis regime
            risk_proba[0] *= 0.2  # Low risk penalty factor
        elif regime_name == "moderate_transition":
            # Moderate penalty for low risk
            drawdown = abs(latest["drawdown"])
            volatility_30d = latest["volatility_30d"]
            if drawdown > 20 or volatility_30d > 0.01:
                risk_proba[0] *= 0.5  # Moderate low risk penalty

        # Check volatility expansion and apply penalty
        predicted_vol = volatility_forecast.get("predicted_volatility_7d", 0)
        current_vol = volatility_forecast.get("current_volatility_7d", 0)
        vol_expansion_ratio = min(predicted_vol / current_vol if current_vol > 0 else 1, 3.0)  # FIX #3: Hard clip at 3.0

        if vol_expansion_ratio > 2.0:
            risk_proba[0] *= 0.5  # Penalize low risk on volatility expansion

        # Check deep drawdown
        drawdown = abs(latest["drawdown"])
        if drawdown > 30:
            risk_proba[0] *= 0.3  # Strong penalty for deep drawdown

        # Re-normalize probabilities to sum to 1.0
        risk_proba = risk_proba / risk_proba.sum()

        # Final classification based on highest adjusted probability
        risk_level = int(np.argmax(risk_proba))
        risk_labels = {0: "low", 1: "medium", 2: "high"}

        # Calculate confidence metrics
        max_confidence = float(risk_proba.max())
        confidence_margin = float(risk_proba[np.argsort(risk_proba)[-1]] - risk_proba[np.argsort(risk_proba)[-2]])
        is_uncertain = max_confidence < 0.65 or confidence_margin < 0.10

        # Warning message for uncertain predictions
        warning = None
        if is_uncertain:
            if confidence_margin < 0.10:
                warning = f"Low confidence margin ({confidence_margin:.3f}) - top 2 classes too close"
            else:
                warning = "Low confidence prediction - treat as weak signal"

        risk_assessment = {
            "risk_level": risk_level,
            "risk_label": risk_labels[risk_level],
            "probabilities": {
                "low": float(risk_proba[0]),
                "medium": float(risk_proba[1]),
                "high": float(risk_proba[2])
            },
            "confidence": max_confidence,
            "confidence_margin": confidence_margin,
            "is_uncertain": bool(is_uncertain),
            "warning": warning,
            "features": {
                "volatility_30d": float(latest["volatility_30d"]),
                "rsi_14": float(latest["rsi_14"]),
                "drawdown": float(latest["drawdown"]),
                "returns_1d": float(latest["returns_1d"])
            },
            "regime_adjustment": regime_name,
            "vol_expansion_ratio": float(vol_expansion_ratio)
        }

        return {
            "risk_assessment": risk_assessment,
            "volatility_forecast": volatility_forecast,
            "market_cluster": market_cluster,
            "market_regime": market_regime
        }

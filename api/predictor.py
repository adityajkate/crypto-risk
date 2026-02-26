"""Model inference service for risk predictions."""
import sys
import types as _types
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.feature_engine import MarketFeatureEngine
from shared.models import EpsilonCalibratedClassifier

# Register EpsilonCalibratedClassifier under every module path it could have
# been pickled with, so joblib deserialization works regardless of origin.
for _mod_name in ("__main__", "__mp_main__", "shared.models", "training.train_risk_classifier"):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _types.ModuleType(_mod_name)
    setattr(sys.modules[_mod_name], "EpsilonCalibratedClassifier", EpsilonCalibratedClassifier)


class RiskPredictor:
    """Load trained models and make risk predictions."""

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.feature_engine = MarketFeatureEngine()
        self._load_models()

    def _load_models(self):
        """Load all trained models from artifacts directory."""
        try:
            self.risk_scaler = joblib.load(self.artifacts_dir / "scaler.joblib")
            raw_risk_model = joblib.load(self.artifacts_dir / "risk_rf.joblib")
            if isinstance(raw_risk_model, EpsilonCalibratedClassifier):
                self.risk_model = raw_risk_model
            else:
                self.risk_model = EpsilonCalibratedClassifier(raw_risk_model, epsilon=1e-4)

            try:
                winsorization = joblib.load(self.artifacts_dir / "winsorization_params.joblib")
                self.percentile_1 = pd.Series(winsorization["percentile_1"])
                self.percentile_99 = pd.Series(winsorization["percentile_99"])
            except FileNotFoundError:
                print("Warning: Winsorization parameters not found, skipping outlier clipping")
                self.percentile_1 = None
                self.percentile_99 = None

            self.volatility_model = joblib.load(self.artifacts_dir / "volatility_linreg.joblib")
            self.volatility_qreg_10 = joblib.load(self.artifacts_dir / "volatility_qreg_10.joblib")
            self.volatility_qreg_50 = joblib.load(self.artifacts_dir / "volatility_qreg_50.joblib")
            self.volatility_qreg_90 = joblib.load(self.artifacts_dir / "volatility_qreg_90.joblib")

            self.cluster_scaler = joblib.load(self.artifacts_dir / "cluster_scaler.joblib")
            self.kmeans_model = joblib.load(self.artifacts_dir / "kmeans_market.joblib")

            self.regime_hmm = joblib.load(self.artifacts_dir / "regime_hmm.joblib")
            self.regime_names = joblib.load(self.artifacts_dir / "regime_names.joblib")

            self.pca_scaler = joblib.load(self.artifacts_dir / "pca_scaler.joblib")
            self.pca_model = joblib.load(self.artifacts_dir / "pca_transformer.joblib")

            self.risk_features = [
                "returns_1d", "log_returns", "volatility_7d", "volatility_30d",
                "rsi_14", "macd", "macd_signal", "macd_hist",
                "bb_width", "atr_14", "obv", "volume_sma_ratio",
                "drawdown", "price_sma50_ratio", "price_sma200_ratio",
                "max_drawdown_30d", "drawdown_duration", "recovery_ratio", "drawdown_vol_interaction",
                "stoch_rsi", "adx", "cci", "willr", "mfi",
                "roc", "momentum", "trix", "ultosc", "aroon_osc", "bop",
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
        """Convert price history to OHLCV DataFrame."""
        df = pd.DataFrame(price_history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    def predict_risk(self, ohlcv_data: pd.DataFrame) -> Dict[str, Any]:
        """Predict risk level for a coin based on OHLCV data.

        Returns:
            Dict with risk_level (0=low, 1=medium, 2=high), probability, and features.
        """
        features_df = self.feature_engine.transform(ohlcv_data)

        if len(features_df) == 0:
            return {"error": "Insufficient data for prediction"}

        latest = features_df.iloc[-1]
        X = latest[self.risk_features].values.reshape(1, -1)
        X = np.nan_to_num(X, 0)

        if self.percentile_1 is not None and self.percentile_99 is not None:
            X_df = pd.DataFrame(X, columns=self.risk_features)
            for col in self.risk_features:
                if col in self.percentile_1.index:
                    X_df[col] = X_df[col].clip(
                        lower=self.percentile_1[col],
                        upper=self.percentile_99[col]
                    )
            X = X_df.values

        X_scaled = self.risk_scaler.transform(X)
        risk_level = int(self.risk_model.predict(X_scaled)[0])
        risk_proba = self.risk_model.predict_proba(X_scaled)[0]

        risk_labels = {0: "low", 1: "medium", 2: "high"}
        max_confidence = float(risk_proba.max())
        confidence_margin = risk_proba[np.argsort(risk_proba)[-1]] - risk_proba[np.argsort(risk_proba)[-2]]
        is_uncertain = max_confidence < 0.65 or confidence_margin < 0.10

        warning = None
        if is_uncertain:
            if confidence_margin < 0.10:
                warning = f"Low confidence margin ({confidence_margin:.3f}) - top 2 classes too close"
            else:
                warning = "Low confidence prediction - treat as weak signal"

        return {
            "risk_level": risk_level,
            "risk_label": risk_labels[risk_level],
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
        vol_features = [
            "volatility_7d", "volatility_30d", "rsi_14", "atr_14",
            "bb_width", "volume_sma_ratio", "drawdown", "price_sma50_ratio", "macd_hist"
        ]
        X = latest[vol_features].values.reshape(1, -1)
        X = np.nan_to_num(X, 0)

        predicted_vol = float(self.volatility_model.predict(X)[0])

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

        recent = features_df.tail(30)
        X = recent[["log_returns", "volatility_7d"]].values
        X = np.nan_to_num(X, 0)

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
        volatility_forecast = self.predict_volatility(ohlcv_data)
        market_cluster = self.predict_market_cluster(ohlcv_data)
        market_regime = self.predict_regime(ohlcv_data)

        features_df = self.feature_engine.transform(ohlcv_data)
        if len(features_df) == 0:
            return {"error": "Insufficient data for prediction"}

        latest = features_df.iloc[-1]
        X = latest[self.risk_features].values.reshape(1, -1)
        X = np.nan_to_num(X, 0)

        if self.percentile_1 is not None and self.percentile_99 is not None:
            X_df = pd.DataFrame(X, columns=self.risk_features)
            for col in self.risk_features:
                if col in self.percentile_1.index:
                    X_df[col] = X_df[col].clip(
                        lower=self.percentile_1[col],
                        upper=self.percentile_99[col]
                    )
            X = X_df.values

        X_scaled = self.risk_scaler.transform(X)
        risk_proba = self.risk_model.predict_proba(X_scaled)[0].copy()

        regime_name = market_regime.get("regime_name", "unknown")

        if regime_name == "high_vol_crisis":
            risk_proba[0] *= 0.2
        elif regime_name == "moderate_transition":
            drawdown = abs(latest["drawdown"])
            volatility_30d = latest["volatility_30d"]
            if drawdown > 20 or volatility_30d > 0.01:
                risk_proba[0] *= 0.5

        predicted_vol = volatility_forecast.get("predicted_volatility_7d", 0)
        current_vol = volatility_forecast.get("current_volatility_7d", 0)
        vol_expansion_ratio = min(predicted_vol / current_vol if current_vol > 0 else 1, 3.0)

        if vol_expansion_ratio > 2.0:
            risk_proba[0] *= 0.5

        drawdown = abs(latest["drawdown"])
        if drawdown > 30:
            risk_proba[0] *= 0.3

        risk_proba = risk_proba / risk_proba.sum()

        risk_level = int(np.argmax(risk_proba))
        risk_labels = {0: "low", 1: "medium", 2: "high"}

        max_confidence = float(risk_proba.max())
        confidence_margin = float(risk_proba[np.argsort(risk_proba)[-1]] - risk_proba[np.argsort(risk_proba)[-2]])
        is_uncertain = max_confidence < 0.65 or confidence_margin < 0.10

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

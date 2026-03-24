import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
import joblib
import json
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.feature_selection import VarianceThreshold
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    brier_score_loss,
    make_scorer,
)
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns

from core.models import EpsilonCalibratedClassifier


class XGBoostRiskTrainer:
    """Focused XGBoost trainer with aggressive regularization to prevent overfitting."""

    FEATURE_COLS = [
        # Returns and Volatility
        "returns_1d",
        "log_returns",
        "volatility_7d",
        "volatility_30d",
        # Classic Indicators
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_lower",
        "bb_width",
        "atr_14",
        "obv",
        "volume_sma_ratio",
        # Drawdown Features
        "drawdown",
        "max_drawdown_30d",
        "drawdown_duration",
        "recovery_ratio",
        "drawdown_vol_interaction",
        # Price Ratios
        "price_sma50_ratio",
        "price_sma200_ratio",
        # Advanced Momentum
        "stoch_rsi",
        "adx",
        "cci",
        "willr",
        "mfi",
        "roc",
        "momentum",
        "trix",
        "ultosc",
        "aroon_osc",
        "bop",
        # Predictive Features
        "price_momentum_5d",
        "price_momentum_10d",
        "price_acceleration",
        "volume_trend_5d",
        "volume_spike",
        "volatility_trend",
        "volatility_acceleration",
        "distance_from_high",
        "distance_from_low",
        "trend_strength",
        "rsi_change",
        "price_rsi_divergence",
    ]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = (
            processed_dir or Path(__file__).parent.parent / "data" / "processed"
        )
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent.parent / "models"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        print("=" * 60)
        print("  XGBoost-Only Risk Classifier Training")
        print("  Goal: Maximize macro-F1 (not weighted)")
        print("=" * 60)

        # Load data
        print("\nLoading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(["timestamp", "coin_id"]).reset_index(drop=True)
        n_coins = df["coin_id"].nunique()
        print(f"Data : {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"Coins: {n_coins}  |  Rows: {len(df)}")

        # Temporal split
        split_idx = int(len(df) * 0.8)
        df_train, df_test = df.iloc[:split_idx], df.iloc[split_idx:]
        y_train = df_train["risk_label"].reset_index(drop=True)
        y_test = df_test["risk_label"].reset_index(drop=True)

        print(
            f"\nTrain: {df_train['timestamp'].min()} to "
            f"{df_train['timestamp'].max()} ({len(df_train)} rows)"
        )
        print(
            f"Test : {df_test['timestamp'].min()} to "
            f"{df_test['timestamp'].max()} ({len(df_test)} rows)"
        )

        # Preprocessing with feature selection and interactions
        X_train, X_test, feature_names = self._preprocess_advanced(df_train, df_test)
        print(f"Total features after engineering: {len(feature_names)}")

        # Class distribution
        print(f"\nClass distribution:")
        for cls in sorted(y_train.unique()):
            cnt = (y_train == cls).sum()
            pct = cnt / len(y_train) * 100
            print(f"  Class {cls}: {cnt:6d} ({pct:5.1f}%)")

        # Train single multiclass model (NOT ordinal - that failed)
        self._train_multiclass_optimized(
            X_train, X_test, y_train, y_test, feature_names
        )

    def _train_multiclass_optimized(
        self, X_train, X_test, y_train, y_test, feature_names
    ):
        """
        Single multiclass XGBoost optimized for macro-F1.

        This works better than ordinal because volatility classes overlap
        rather than forming clean monotonic boundaries.
        """
        print("\n" + "=" * 60)
        print("  MULTICLASS XGBoost (Macro-F1 Optimized)")
        print("  Single model with proper feature engineering")
        print("=" * 60)

        # Calculate class weights
        class_counts = np.bincount(y_train)
        total = len(y_train)
        class_weights = {
            i: total / (len(class_counts) * count)
            for i, count in enumerate(class_counts)
        }

        print("\nClass distribution:")
        for cls in range(len(class_counts)):
            cnt = class_counts[cls]
            pct = cnt / total * 100
            weight = class_weights[cls]
            print(f"  Class {cls}: {cnt:6d} ({pct:5.1f}%)  weight={weight:.3f}")

        # Optimized parameters for multiclass with better generalization
        best_params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "max_depth": 5,  # Shallower to reduce overfitting
            "n_estimators": 400,
            "learning_rate": 0.05,  # Faster learning with fewer trees
            "subsample": 0.70,  # More aggressive subsampling
            "colsample_bytree": 0.65,
            "colsample_bylevel": 0.65,
            "colsample_bynode": 0.70,
            "reg_alpha": 3.0,  # Very strong L1
            "reg_lambda": 7.0,  # Very strong L2
            "min_child_weight": 20,  # Very conservative splits
            "gamma": 1.0,  # Aggressive pruning
            "random_state": 42,
            "tree_method": "hist",
            "eval_metric": "mlogloss",
        }

        print("\nModel parameters:")
        for k, v in best_params.items():
            if k not in [
                "objective",
                "num_class",
                "random_state",
                "tree_method",
                "eval_metric",
            ]:
                print(f"  {k:20s}: {v}")

        # Stronger sample weights for Medium class
        sample_weights = np.array([class_weights[y] ** 1.2 for y in y_train])

        print(
            f"\nSample weight range: {sample_weights.min():.3f} to {sample_weights.max():.3f}"
        )
        print(
            f"Sample weight ratio: {sample_weights.max() / sample_weights.min():.2f}x"
        )

        # Early stopping
        print("\nTraining with early stopping...")
        split_idx = int(len(X_train) * 0.85)
        X_tr, X_val = X_train[:split_idx], X_train[split_idx:]
        y_tr, y_val = y_train.iloc[:split_idx], y_train.iloc[split_idx:]
        sw_tr = sample_weights[:split_idx]

        model_es = xgb.XGBClassifier(**best_params, early_stopping_rounds=50)
        model_es.fit(
            X_tr, y_tr, sample_weight=sw_tr, eval_set=[(X_val, y_val)], verbose=False
        )

        best_iter = model_es.best_iteration
        print(f"Early stopping at iteration: {best_iter}")

        # Retrain on full data
        best_params["n_estimators"] = best_iter
        print(f"\nRetraining on full training set with n_estimators={best_iter}...")

        final_model = xgb.XGBClassifier(**best_params)
        final_model.fit(X_train, y_train, sample_weight=sample_weights, verbose=False)

        wrapped = EpsilonCalibratedClassifier(final_model, epsilon=1e-4)

        # Evaluate
        y_pred = wrapped.predict(X_test)
        y_proba = wrapped.predict_proba(X_test)
        y_train_pred = wrapped.predict(X_train)

        train_f1_weighted = f1_score(y_train, y_train_pred, average="weighted")
        train_f1_macro = f1_score(y_train, y_train_pred, average="macro")

        test_p, test_r, test_f1_weighted, _ = precision_recall_fscore_support(
            y_test, y_pred, average="weighted"
        )
        test_f1_macro = f1_score(y_test, y_pred, average="macro")

        gap_weighted = train_f1_weighted - test_f1_weighted
        gap_macro = train_f1_macro - test_f1_macro

        per_class_f1 = f1_score(y_test, y_pred, average=None)

        # Brier score
        brier_per_class = []
        for c in range(y_proba.shape[1]):
            brier_per_class.append(
                brier_score_loss((y_test == c).astype(int), y_proba[:, c])
            )
        avg_brier = np.mean(brier_per_class)

        # Confidence distribution
        max_p = y_proba.max(axis=1)
        low_conf = (max_p < 0.65).mean() * 100
        high_conf = (max_p >= 0.80).mean() * 100

        print("\n" + "=" * 60)
        print("  RESULTS")
        print("=" * 60)

        print(f"\nWeighted F1:")
        print(f"  Train: {train_f1_weighted:.4f}")
        print(f"  Test:  {test_f1_weighted:.4f}  (P={test_p:.4f}  R={test_r:.4f})")
        print(f"  Gap:   {gap_weighted:+.4f}")

        print(f"\nMacro F1 (MAIN METRIC):")
        print(f"  Train: {train_f1_macro:.4f}")
        print(f"  Test:  {test_f1_macro:.4f}")
        print(f"  Gap:   {gap_macro:+.4f}  {'[OK]' if gap_macro <= 0.10 else '[WARN]'}")

        print(f"\nPer-Class F1:")
        print(f"  Low (0):    {per_class_f1[0]:.4f}")
        print(f"  Medium (1): {per_class_f1[1]:.4f}")
        print(f"  High (2):   {per_class_f1[2]:.4f}")

        print(
            f"\nBrier:      {avg_brier:.4f}  {'[OK]' if avg_brier < 0.25 else '[WARN]'}"
        )
        print(f"Confidence: {low_conf:.1f}% low  |  {high_conf:.1f}% high")

        print(f"\nClassification Report:")
        print(
            classification_report(y_test, y_pred, target_names=["Low", "Med", "High"])
        )

        # Save model
        joblib.dump(wrapped, self.artifacts_dir / "risk_xgb_optimized.joblib")
        print(f"\nSaved risk_xgb_optimized.joblib")

        # Save confusion matrix and feature importance
        cm = confusion_matrix(y_test, y_pred)
        self._plot_confusion_matrix(cm)
        self._plot_feature_importance(final_model, feature_names)

        # Save metadata
        metadata = {
            "model": "multiclass_xgboost",
            "optimization_metric": "macro_f1",
            "train_f1_macro": float(train_f1_macro),
            "train_f1_weighted": float(train_f1_weighted),
            "test_f1_macro": float(test_f1_macro),
            "test_f1_weighted": float(test_f1_weighted),
            "test_precision": float(test_p),
            "test_recall": float(test_r),
            "gap_macro": float(gap_macro),
            "gap_weighted": float(gap_weighted),
            "per_class_f1": {
                "low": float(per_class_f1[0]),
                "medium": float(per_class_f1[1]),
                "high": float(per_class_f1[2]),
            },
            "brier": float(avg_brier),
            "best_params": {k: str(v) for k, v in best_params.items()},
            "confusion_matrix": cm.tolist(),
            "classification_report": classification_report(
                y_test, y_pred, output_dict=True
            ),
            "class_distribution": {
                "train": {int(k): int(v) for k, v in enumerate(class_counts)},
                "train_percentages": {
                    int(k): float(v / total * 100) for k, v in enumerate(class_counts)
                },
            },
            "confidence_distribution": {
                "low_confidence_pct": float(low_conf),
                "high_confidence_pct": float(high_conf),
            },
        }

        with open(self.artifacts_dir / "xgb_optimized_metrics.json", "w") as f:
            json.dump(metadata, f, indent=2)

        print("\n" + "=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        print(f"Macro F1:  {test_f1_macro:.4f}")
        print(
            f"Gap:       {gap_macro:+.4f} {'[GOOD]' if gap_macro <= 0.10 else '[NEEDS WORK]'}"
        )
        print(f"Medium F1: {per_class_f1[1]:.4f}")
        print("=" * 60)

    def _preprocess_advanced(self, df_train, df_test):
        """Advanced preprocessing: cross-sectional features + nonlinear interactions."""
        print("\nAdding cross-sectional features...")

        # Add market-relative features
        df_train = self._add_cross_sectional_features(df_train)
        df_test = self._add_cross_sectional_features(df_test)

        # Extended feature list with cross-sectional
        feature_cols = self.FEATURE_COLS + [
            "returns_zscore",
            "vol_zscore",
            "momentum_zscore",
            "returns_percentile",
            "vol_percentile",
            "momentum_percentile",
        ]

        X_tr = df_train[feature_cols].copy()
        X_te = df_test[feature_cols].copy()

        # Median imputation
        medians = X_tr.median()
        X_tr = X_tr.fillna(medians)
        X_te = X_te.fillna(medians)

        # Replace inf
        X_tr = X_tr.replace([np.inf, -np.inf], np.nan).fillna(0)
        X_te = X_te.replace([np.inf, -np.inf], np.nan).fillna(0)

        # STEP 1: Remove weak features (low variance)
        print("\nFeature selection:")
        var_selector = VarianceThreshold(threshold=0.01)
        var_selector.fit(X_tr)

        removed_low_var = (~var_selector.get_support()).sum()
        print(f"  Removed {removed_low_var} low-variance features")

        X_tr = pd.DataFrame(
            var_selector.transform(X_tr),
            columns=np.array(feature_cols)[var_selector.get_support()],
        )
        X_te = pd.DataFrame(var_selector.transform(X_te), columns=X_tr.columns)

        # STEP 2: Add nonlinear interaction features
        print(f"\nAdding interaction features...")
        X_tr, X_te, interaction_names = self._add_interaction_features(X_tr, X_te)

        final_feature_names = list(X_tr.columns) + interaction_names
        print(f"  Total features after interactions: {len(final_feature_names)}")

        # Scale
        scaler = StandardScaler()
        X_tr_arr = scaler.fit_transform(X_tr)
        X_te_arr = scaler.transform(X_te)

        # Winsorize
        p1 = np.percentile(X_tr_arr, 1, axis=0)
        p99 = np.percentile(X_tr_arr, 99, axis=0)
        X_tr_arr = np.clip(X_tr_arr, p1, p99)
        X_te_arr = np.clip(X_te_arr, p1, p99)

        # Save artifacts
        joblib.dump(scaler, self.artifacts_dir / "scaler_xgb.joblib")
        joblib.dump(
            medians.to_dict(), self.artifacts_dir / "imputation_medians_xgb.joblib"
        )
        joblib.dump(
            {"p1": p1.tolist(), "p99": p99.tolist()},
            self.artifacts_dir / "winsorization_params_xgb.joblib",
        )
        joblib.dump(var_selector, self.artifacts_dir / "var_selector_xgb.joblib")

        return X_tr_arr, X_te_arr, final_feature_names

    def _add_interaction_features(self, X_tr, X_te):
        """Add key nonlinear interaction features for tree models."""
        # Key interactions that capture risk dynamics
        interactions = []
        names = []

        # Volatility * Volume interactions (high vol + high volume = risk)
        if "volatility_7d" in X_tr.columns and "volume_spike" in X_tr.columns:
            interactions.append(
                X_tr["volatility_7d"].values * X_tr["volume_spike"].values
            )
            names.append("vol_volume_interaction")

        # Momentum * Volatility (momentum in high vol = risk)
        if "price_momentum_5d" in X_tr.columns and "volatility_7d" in X_tr.columns:
            interactions.append(
                X_tr["price_momentum_5d"].values * X_tr["volatility_7d"].values
            )
            names.append("momentum_vol_interaction")

        # RSI * Volatility (extreme RSI in high vol = risk)
        if "rsi_14" in X_tr.columns and "volatility_7d" in X_tr.columns:
            interactions.append(X_tr["rsi_14"].values * X_tr["volatility_7d"].values)
            names.append("rsi_vol_interaction")

        # Drawdown * Volatility acceleration (already exists but ensure it's used)
        if "drawdown" in X_tr.columns and "volatility_acceleration" in X_tr.columns:
            interactions.append(
                X_tr["drawdown"].values * X_tr["volatility_acceleration"].values
            )
            names.append("dd_volacc_interaction")

        # Cross-sectional * base features
        if "returns_zscore" in X_tr.columns and "volatility_7d" in X_tr.columns:
            interactions.append(
                X_tr["returns_zscore"].values * X_tr["volatility_7d"].values
            )
            names.append("returns_z_vol")

        if "vol_zscore" in X_tr.columns and "momentum_zscore" in X_tr.columns:
            interactions.append(
                X_tr["vol_zscore"].values * X_tr["momentum_zscore"].values
            )
            names.append("vol_z_momentum_z")

        # Build test interactions
        interactions_te = []
        if "volatility_7d" in X_te.columns and "volume_spike" in X_te.columns:
            interactions_te.append(
                X_te["volatility_7d"].values * X_te["volume_spike"].values
            )

        if "price_momentum_5d" in X_te.columns and "volatility_7d" in X_te.columns:
            interactions_te.append(
                X_te["price_momentum_5d"].values * X_te["volatility_7d"].values
            )

        if "rsi_14" in X_te.columns and "volatility_7d" in X_te.columns:
            interactions_te.append(X_te["rsi_14"].values * X_te["volatility_7d"].values)

        if "drawdown" in X_te.columns and "volatility_acceleration" in X_te.columns:
            interactions_te.append(
                X_te["drawdown"].values * X_te["volatility_acceleration"].values
            )

        if "returns_zscore" in X_te.columns and "volatility_7d" in X_te.columns:
            interactions_te.append(
                X_te["returns_zscore"].values * X_te["volatility_7d"].values
            )

        if "vol_zscore" in X_te.columns and "momentum_zscore" in X_te.columns:
            interactions_te.append(
                X_te["vol_zscore"].values * X_te["momentum_zscore"].values
            )

        # Concatenate
        if interactions:
            X_tr_new = np.column_stack([X_tr.values] + interactions)
            X_te_new = np.column_stack([X_te.values] + interactions_te)
            X_tr = pd.DataFrame(X_tr_new, columns=list(X_tr.columns) + names)
            X_te = pd.DataFrame(X_te_new, columns=list(X_te.columns) + names)

        print(f"  Added {len(names)} interaction features")

        return X_tr, X_te, names

    def _add_cross_sectional_features(self, df):
        """Add features comparing each coin to the market at each timestamp."""
        df = df.copy()

        # Group by timestamp to get market stats
        for col, prefix in [
            ("returns_1d", "returns"),
            ("volatility_7d", "vol"),
            ("price_momentum_5d", "momentum"),
        ]:
            if col in df.columns:
                # Z-score relative to market
                df[f"{prefix}_zscore"] = df.groupby("timestamp")[col].transform(
                    lambda x: (x - x.mean()) / (x.std() + 1e-8)
                )

                # Percentile rank relative to market
                df[f"{prefix}_percentile"] = df.groupby("timestamp")[col].transform(
                    lambda x: x.rank(pct=True)
                )

        return df

    def _plot_confusion_matrix(self, cm):
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=["Low", "Medium", "High"],
            yticklabels=["Low", "Medium", "High"],
        )
        plt.title("Confusion Matrix - XGBoost Optimized")
        plt.ylabel("True Label")
        plt.xlabel("Predicted Label")
        plt.tight_layout()
        plt.savefig(self.artifacts_dir / "confusion_matrix_xgb_optimized.png", dpi=150)
        plt.close()
        print("Saved confusion_matrix_xgb_optimized.png")

    def _plot_feature_importance(self, model, feature_names):
        importances = model.feature_importances_
        top_n = min(20, len(importances))
        idx = np.argsort(importances)[::-1][:top_n]

        labels = [feature_names[i] for i in idx]

        plt.figure(figsize=(10, 8))
        plt.title(f"Top {top_n} Features - XGBoost Optimized")
        plt.barh(range(top_n), importances[idx], color="steelblue")
        plt.yticks(range(top_n), labels, fontsize=9)
        plt.xlabel("Importance")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(
            self.artifacts_dir / "feature_importance_xgb_optimized.png", dpi=150
        )
        plt.close()
        print("Saved feature_importance_xgb_optimized.png")


def main():
    trainer = XGBoostRiskTrainer()
    trainer.run()


if __name__ == "__main__":
    main()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import joblib
import json
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    brier_score_loss,
)
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns

from shared.models import EpsilonCalibratedClassifier


class RiskClassifierTrainer:
    """Train risk classification models."""

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
        "bb_width",
        "atr_14",
        "obv",
        "volume_sma_ratio",
        "drawdown",
        "price_sma50_ratio",
        "price_sma200_ratio",
        # Enhanced Drawdown Features (PRIORITY 4)
        "max_drawdown_30d",
        "drawdown_duration",
        "recovery_ratio",
        "drawdown_vol_interaction",
        # Advanced Momentum Indicators
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
        # Regime Features (PRIORITY 6)
        "regime_volatility_interaction",
        "regime_drawdown_interaction",
    ]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = (
            processed_dir or Path(__file__).parent / "data" / "processed"
        )
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        """Train all risk classifiers."""
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")

        # PRIORITY 1: Ensure strict time-series ordering
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(["coin_id", "timestamp"]).reset_index(drop=True)
        print(
            f"Data sorted by time: {df['timestamp'].min()} to {df['timestamp'].max()}"
        )

        X = df[self.FEATURE_COLS].fillna(0)
        y = df["risk_label"]

        # Create train/test split (80/20) with temporal ordering
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        print(
            f"Train period: {df.iloc[:split_idx]['timestamp'].min()} to {df.iloc[split_idx-1]['timestamp']}"
        )
        print(
            f"Test period:  {df.iloc[split_idx]['timestamp']} to {df.iloc[-1]['timestamp']}"
        )

        # FIX #2: Winsorization - clip outliers at 1st and 99th percentiles
        print("\nApplying Winsorization (1st-99th percentile clipping)...")
        percentile_1 = X_train.quantile(0.01)
        percentile_99 = X_train.quantile(0.99)

        X_train_clipped = X_train.clip(lower=percentile_1, upper=percentile_99, axis=1)
        X_test_clipped = X_test.clip(lower=percentile_1, upper=percentile_99, axis=1)

        # Scale features (fit on train only - no leakage)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_clipped)
        X_test_scaled = scaler.transform(X_test_clipped)

        # FIX #1: Split training data for calibration BEFORE model training
        # 80% for base model training, 20% for calibration (holdout)
        base_split_idx = int(len(X_train_scaled) * 0.8)
        X_base_train = X_train_scaled[:base_split_idx]
        X_calibration = X_train_scaled[base_split_idx:]
        y_base_train = y_train.iloc[:base_split_idx]
        y_calibration = y_train.iloc[base_split_idx:]

        print(f"\nBase training set: {len(X_base_train)} samples")
        print(f"Calibration set: {len(X_calibration)} samples (holdout)")
        print(f"Test set: {len(X_test)} samples")

        # Save scaler and Winsorization parameters
        joblib.dump(scaler, self.artifacts_dir / "scaler.joblib")
        joblib.dump({
            "percentile_1": percentile_1.to_dict(),
            "percentile_99": percentile_99.to_dict()
        }, self.artifacts_dir / "winsorization_params.joblib")
        print("Saved scaler.joblib and winsorization_params.joblib")

        # Define models with adjusted regularization (PRIORITY 7)
        # Reduced regularization to allow extreme predictions after calibration
        models = {
            "logreg": LogisticRegression(
                multi_class="multinomial",
                max_iter=2000,
                C=10.0,  # Increased from 1.0 to reduce regularization
                class_weight="balanced",
                random_state=42,
            ),
            "rf": RandomForestClassifier(
                n_estimators=500,
                max_depth=20,  # Increased from 15 to allow deeper trees
                min_samples_split=5,  # Reduced from 10 to allow more splits
                min_samples_leaf=5,  # Reduced from 15 to allow smaller leaves
                max_features="sqrt",
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ),
            "xgb": xgb.XGBClassifier(
                n_estimators=300,
                max_depth=8,  # Increased from 6 to allow deeper trees
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.01,  # Reduced from 0.1 (less L1 regularization)
                reg_lambda=0.5,  # Reduced from 1.0 (less L2 regularization)
                min_child_weight=1,  # Reduced from 3 to allow more extreme splits
                objective="multi:softprob",
                num_class=3,
                random_state=42,
                # Note: early_stopping_rounds removed for cross-validation compatibility
            ),
        }

        results = {}
        all_metrics = {}
        tscv = TimeSeriesSplit(n_splits=5)

        for name, model in models.items():
            print(f"\nTraining {name}...")

            # Cross-validation on base training set only
            if name == "xgb":
                scores = cross_val_score(
                    model, X_base_train, y_base_train, cv=tscv, scoring="accuracy"
                )
                print(f"  CV Accuracy: {scores.mean():.4f} (+/- {scores.std():.4f})")

                # Train with early stopping - use part of base training for validation
                val_split = int(len(X_base_train) * 0.8)
                X_tr, X_val = X_base_train[:val_split], X_base_train[val_split:]
                y_tr, y_val = y_base_train.iloc[:val_split], y_base_train.iloc[val_split:]

                # Create new model with early stopping for final training
                model_with_early_stop = xgb.XGBClassifier(
                    n_estimators=300,
                    max_depth=8,  # Increased from 6
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_alpha=0.01,  # Reduced from 0.1
                    reg_lambda=0.5,  # Reduced from 1.0
                    min_child_weight=1,  # Reduced from 3
                    objective="multi:softprob",
                    num_class=3,
                    random_state=42,
                    early_stopping_rounds=30,
                    eval_metric="mlogloss",
                )

                model_with_early_stop.fit(
                    X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False
                )
                print(f"  Best iteration: {model_with_early_stop.best_iteration}")
                model = model_with_early_stop  # Use the early-stopped model
            else:
                scores = cross_val_score(
                    model, X_base_train, y_base_train, cv=tscv, scoring="f1_weighted"
                )
                print(f"  CV F1: {scores.mean():.4f} (+/- {scores.std():.4f})")
                model.fit(X_base_train, y_base_train)

            # FIX #1: Calibrate probabilities on HOLDOUT calibration set (no leakage)
            print(f"  Calibrating probabilities on holdout set...")
            calibrated_model = CalibratedClassifierCV(
                model, method="isotonic", cv="prefit"
            )
            calibrated_model.fit(X_calibration, y_calibration)

            # FIX #2: Apply epsilon floor to prevent probability collapse to 0.0
            model = EpsilonCalibratedClassifier(calibrated_model, epsilon=1e-4)

            # Evaluate on test set
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)
            # Evaluate on full training set (base + calibration combined)
            y_train_pred = model.predict(X_train_scaled)

            # Calculate Brier score for probability calibration quality
            # Convert to binary format for each class
            brier_scores = []
            for i in range(3):
                y_binary = (y_test == i).astype(int)
                brier = brier_score_loss(y_binary, y_pred_proba[:, i])
                brier_scores.append(brier)
            avg_brier = np.mean(brier_scores)

            # Check confidence thresholds
            max_proba = y_pred_proba.max(axis=1)
            low_confidence_pct = (max_proba < 0.65).sum() / len(max_proba) * 100
            high_confidence_pct = (max_proba >= 0.80).sum() / len(max_proba) * 100

            # Calculate metrics for both train and test
            train_f1 = f1_score(y_train, y_train_pred, average="weighted")
            test_precision, test_recall, test_f1, support = (
                precision_recall_fscore_support(y_test, y_pred, average="weighted")
            )

            print(f"\n  Training Set Performance:")
            print(f"    F1 Score: {train_f1:.4f}")
            print(f"\n  Test Set Performance:")
            print(f"    Precision: {test_precision:.4f}")
            print(f"    Recall: {test_recall:.4f}")
            print(f"    F1 Score: {test_f1:.4f}")
            print(f"\n  Probability Calibration:")
            print(f"    Brier Score: {avg_brier:.4f} (lower is better, <0.25 is good)")
            print(f"    Low confidence (<0.65): {low_confidence_pct:.1f}%")
            print(f"    High confidence (>=0.80): {high_confidence_pct:.1f}%")

            # Check for overfitting/underfitting
            f1_gap = train_f1 - test_f1
            if f1_gap > 0.10:
                print(f"  WARNING: Possible OVERFITTING (train-test gap: {f1_gap:.4f})")
            elif test_f1 < 0.70:
                print(f"  WARNING: Possible UNDERFITTING (test F1: {test_f1:.4f})")
            else:
                print(f"  Good generalization (train-test gap: {f1_gap:.4f})")

            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            self._plot_confusion_matrix(cm, name)

            # Feature importance (for tree-based models)
            if name in ["rf", "xgb"]:
                self._plot_feature_importance(model, name)

            # Save metrics
            all_metrics[name] = {
                "cv_score": float(scores.mean()),
                "cv_std": float(scores.std()),
                "train_f1": float(train_f1),
                "test_precision": float(test_precision),
                "test_recall": float(test_recall),
                "test_f1": float(test_f1),
                "train_test_gap": float(f1_gap),
                "overfitting_warning": bool(f1_gap > 0.10),
                "underfitting_warning": bool(test_f1 < 0.70),
                "brier_score": float(avg_brier),
                "low_confidence_pct": float(low_confidence_pct),
                "high_confidence_pct": float(high_confidence_pct),
                "calibration_quality": "good" if avg_brier < 0.25 else "poor",
                "confusion_matrix": cm.tolist(),
                "classification_report": classification_report(
                    y_test, y_pred, output_dict=True
                ),
            }

            # Save model
            joblib.dump(model, self.artifacts_dir / f"risk_{name}.joblib")
            print(f"  Saved risk_{name}.joblib")

            results[name] = scores.mean()

        # Save all metrics to JSON
        with open(self.artifacts_dir / "training_metrics.json", "w") as f:
            json.dump(all_metrics, f, indent=2)
        print("\nSaved training_metrics.json")

        # Save best model metadata
        best_model = max(results, key=results.get)
        metadata = {
            "best_model": best_model,
            "best_score": results[best_model],
            "all_scores": results,
            "features": self.FEATURE_COLS,
            "num_features": len(self.FEATURE_COLS),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
        }
        joblib.dump(metadata, self.artifacts_dir / "risk_best.joblib")
        print(f"\nBest model: {best_model} (F1: {results[best_model]:.4f})")

    def _plot_confusion_matrix(self, cm, model_name):
        """Plot and save confusion matrix."""
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=["Low", "Medium", "High"],
            yticklabels=["Low", "Medium", "High"],
        )
        plt.title(f"Confusion Matrix - {model_name.upper()}")
        plt.ylabel("True Label")
        plt.xlabel("Predicted Label")
        plt.tight_layout()
        plt.savefig(self.artifacts_dir / f"confusion_matrix_{model_name}.png", dpi=150)
        plt.close()
        print(f"  Saved confusion_matrix_{model_name}.png")

    def _plot_feature_importance(self, model, model_name):
        """Plot and save feature importance."""
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1][:20]  # Top 20 features

            plt.figure(figsize=(10, 8))
            plt.title(f"Top 20 Feature Importances - {model_name.upper()}")
            plt.barh(range(len(indices)), importances[indices])
            plt.yticks(range(len(indices)), [self.FEATURE_COLS[i] for i in indices])
            plt.xlabel("Importance")
            plt.tight_layout()
            plt.savefig(
                self.artifacts_dir / f"feature_importance_{model_name}.png", dpi=150
            )
            plt.close()
            print(f"  Saved feature_importance_{model_name}.png")


def main():
    trainer = RiskClassifierTrainer()
    trainer.run()


if __name__ == "__main__":
    main()

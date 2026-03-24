import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
import joblib
import json
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.feature_selection import mutual_info_classif
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


class RiskClassifierTrainer:
    """Train risk classification models with automatic hyperparameter tuning."""

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
        # Enhanced Drawdown Features
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
        # Regime Features
        "regime_volatility_interaction",
        "regime_drawdown_interaction",
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

    INTERACTION_KEYS = [
        "returns_1d",
        "volatility_7d",
        "rsi_14",
        "drawdown",
        "volume_spike",
        "price_momentum_5d",
        "volatility_trend",
        "macd",
    ]

    def __init__(self, processed_dir: Path = None, artifacts_dir: Path = None):
        self.processed_dir = (
            processed_dir or Path(__file__).parent.parent / "data" / "processed"
        )
        self.artifacts_dir = artifacts_dir or Path(__file__).parent.parent.parent / "models"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # ==============================================================
    #  MAIN PIPELINE
    # ==============================================================
    def run(self) -> None:
        # ── 1. LOAD & SORT ───────────────────────────────────────
        print("Loading data...")
        df = pd.read_csv(self.processed_dir / "features_with_labels.csv")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(["timestamp", "coin_id"]).reset_index(drop=True)
        n_coins = df["coin_id"].nunique()
        print(f"Data : {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"Coins: {n_coins}  |  Rows: {len(df)}")

        # ── 2. TEMPORAL SPLIT (before any preprocessing) ─────────
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

        # ── 3. PREPROCESSING (all fit on train only) ─────────────
        X_train, X_test, feature_names = self._preprocess(df_train, df_test)
        print(f"Total features: {len(feature_names)}")

        # ── 4. DATA DIAGNOSTICS ──────────────────────────────────
        self._diagnose(X_train, y_train, feature_names)

        # ── 5. HYPERPARAMETER SEARCH ─────────────────────────────
        tscv = TimeSeriesSplit(n_splits=5, gap=max(5, n_coins))
        f1w = make_scorer(f1_score, average="weighted")

        tuned = self._tune_models(X_train, y_train, tscv, f1w)

        # ── 6. FINAL TRAINING + EVALUATION ───────────────────────
        results = {}
        all_metrics = {}
        final_models = {}

        for name, (best_est, cv_score, best_params, cv_train_f1) in tuned.items():
            print(f"\n{'=' * 60}")
            print(f"  {name.upper()}")
            print(f"{'=' * 60}")

            # ── Re-train on full train set with best params ──────
            # For XGB: add balanced sample_weight (not available in search)
            if name == "xgb":
                xgb_base = {
                    "objective": "multi:softprob",
                    "num_class": 3,
                    "random_state": 42,
                    "tree_method": "hist",
                }
                model = xgb.XGBClassifier(**xgb_base, **best_params)
                sw = compute_sample_weight("balanced", y_train)
                model.fit(X_train, y_train, sample_weight=sw)
            elif name == "gb":
                gb_base = {"random_state": 42}
                model = GradientBoostingClassifier(**gb_base, **best_params)
                sw = compute_sample_weight("balanced", y_train)
                model.fit(X_train, y_train, sample_weight=sw)
            else:
                # LR/RF already have class_weight='balanced'
                model = best_est  # already fitted by refit=True

            wrapped = EpsilonCalibratedClassifier(model, epsilon=1e-4)

            # ── Evaluate ─────────────────────────────────────────
            y_pred = wrapped.predict(X_test)
            y_proba = wrapped.predict_proba(X_test)
            y_train_pred = wrapped.predict(X_train)

            train_f1 = f1_score(y_train, y_train_pred, average="weighted")
            test_p, test_r, test_f1, _ = precision_recall_fscore_support(
                y_test, y_pred, average="weighted"
            )
            gap = train_f1 - test_f1

            brier_per_class = []
            for c in range(y_proba.shape[1]):
                brier_per_class.append(
                    brier_score_loss((y_test == c).astype(int), y_proba[:, c])
                )
            avg_brier = np.mean(brier_per_class)

            max_p = y_proba.max(axis=1)
            low_conf = (max_p < 0.65).mean() * 100
            high_conf = (max_p >= 0.80).mean() * 100

            status = "[OK]" if gap <= 0.10 and test_f1 >= 0.50 else "[WARN]"

            print(f"  Best params : {best_params}")
            print(f"  CV Train F1 : {cv_train_f1:.4f}")
            print(
                f"  CV Val   F1 : {cv_score:.4f}  (gap in CV: {cv_train_f1 - cv_score:+.4f})"
            )
            print(f"  Full Train  : {train_f1:.4f}")
            print(f"  Test F1     : {test_f1:.4f}  (P={test_p:.4f}  R={test_r:.4f})")
            print(f"  Train-Test  : {gap:+.4f}  {status}")
            print(
                f"  Brier       : {avg_brier:.4f}  {'[OK]' if avg_brier < 0.25 else '[WARN]'}"
            )
            print(f"  Confidence  : {low_conf:.1f}% low  |  {high_conf:.1f}% high")

            print(f"\n  Classification Report:")
            print(
                classification_report(
                    y_test, y_pred, target_names=["Low", "Med", "High"]
                )
            )

            cm = confusion_matrix(y_test, y_pred)
            self._plot_confusion_matrix(cm, name)
            if name in ("rf", "xgb", "gb"):
                self._plot_feature_importance(wrapped, name, feature_names)

            all_metrics[name] = {
                "cv_train_f1": float(cv_train_f1),
                "cv_val_f1": float(cv_score),
                "train_f1": float(train_f1),
                "test_f1": float(test_f1),
                "test_precision": float(test_p),
                "test_recall": float(test_r),
                "gap": float(gap),
                "brier": float(avg_brier),
                "low_confidence_pct": float(low_conf),
                "high_confidence_pct": float(high_conf),
                "best_params": {k: str(v) for k, v in best_params.items()},
                "confusion_matrix": cm.tolist(),
                "classification_report": classification_report(
                    y_test, y_pred, output_dict=True
                ),
            }
            results[name] = cv_score
            final_models[name] = wrapped
            joblib.dump(wrapped, self.artifacts_dir / f"risk_{name}.joblib")
            print(f"  Saved risk_{name}.joblib")

        # ── 7. WEIGHTED ENSEMBLE ─────────────────────────────────
        print(f"\n{'=' * 60}")
        print("  WEIGHTED ENSEMBLE")
        print(f"{'=' * 60}")

        names_list = list(final_models.keys())
        cv_arr = np.array([results[n] for n in names_list])
        # Sharpen weights so better models count more
        weights = np.exp(cv_arr * 10)
        weights = weights / weights.sum()
        print(f"  Weights: {dict(zip(names_list, weights.round(3)))}")

        test_probas = np.array(
            [final_models[n].predict_proba(X_test) for n in names_list]
        )
        ens_proba = np.average(test_probas, axis=0, weights=weights)
        ens_pred = np.argmax(ens_proba, axis=1)

        train_probas = np.array(
            [final_models[n].predict_proba(X_train) for n in names_list]
        )
        ens_train_proba = np.average(train_probas, axis=0, weights=weights)
        ens_train_pred = np.argmax(ens_train_proba, axis=1)

        ens_train_f1 = f1_score(y_train, ens_train_pred, average="weighted")
        ens_p, ens_r, ens_f1, _ = precision_recall_fscore_support(
            y_test, ens_pred, average="weighted"
        )
        ens_gap = ens_train_f1 - ens_f1

        print(f"  Train F1: {ens_train_f1:.4f}")
        print(f"  Test  F1: {ens_f1:.4f}  (P={ens_p:.4f}  R={ens_r:.4f})")
        print(f"  Gap     : {ens_gap:+.4f}")
        print(f"\n  Classification Report:")
        print(
            classification_report(y_test, ens_pred, target_names=["Low", "Med", "High"])
        )

        cm = confusion_matrix(y_test, ens_pred)
        self._plot_confusion_matrix(cm, "ensemble")

        all_metrics["ensemble"] = {
            "weights": {n: float(w) for n, w in zip(names_list, weights)},
            "train_f1": float(ens_train_f1),
            "test_f1": float(ens_f1),
            "gap": float(ens_gap),
            "confusion_matrix": cm.tolist(),
            "classification_report": classification_report(
                y_test, ens_pred, output_dict=True
            ),
        }
        results["ensemble"] = ens_f1

        # ── 8. SAVE ARTIFACTS ────────────────────────────────────
        with open(self.artifacts_dir / "training_metrics.json", "w") as f:
            json.dump(all_metrics, f, indent=2, default=str)

        best_name = max(results, key=results.get)
        metadata = {
            "best_model": best_name,
            "best_score": float(results[best_name]),
            "all_scores": {k: float(v) for k, v in results.items()},
            "features": self.FEATURE_COLS,
            "final_feature_names": feature_names,
            "n_features": len(feature_names),
            "train_samples": int(len(X_train)),
            "test_samples": int(len(X_test)),
        }
        joblib.dump(metadata, self.artifacts_dir / "risk_best.joblib")

        # ── SUMMARY ──────────────────────────────────────────────
        print(f"\n{'=' * 60}")
        print("  FINAL SUMMARY")
        print(f"{'=' * 60}")
        for n in results:
            m = all_metrics[n]
            flag = "[OK]" if m["gap"] <= 0.10 and m["test_f1"] >= 0.50 else "[WARN]"
            tr = m.get("train_f1", 0)
            te = m["test_f1"]
            g = m["gap"]
            print(f"  {flag} {n:10s}  train={tr:.4f}  test={te:.4f}  gap={g:+.4f}")
        print(f"\n  Best: {best_name}  (score={results[best_name]:.4f})")
        print(f"{'═' * 60}")

    # ==============================================================
    #  PREPROCESSING
    # ==============================================================
    def _preprocess(self, df_train, df_test):
        """All preprocessing with train-only fitting. NO feature removal."""
        X_tr = df_train[self.FEATURE_COLS].copy()
        X_te = df_test[self.FEATURE_COLS].copy()

        # ── Median imputation (not fillna(0)) ────────────────────
        medians = X_tr.median()
        X_tr = X_tr.fillna(medians)
        X_te = X_te.fillna(medians)

        # ── Interaction features (fit on train only) ─────────────
        poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
        tr_poly = poly.fit_transform(X_tr[self.INTERACTION_KEYS])
        te_poly = poly.transform(X_te[self.INTERACTION_KEYS])

        names = poly.get_feature_names_out(self.INTERACTION_KEYS)
        new_mask = [n not in self.INTERACTION_KEYS for n in names]
        new_names = [n for n, m in zip(names, new_mask) if m]

        X_tr = pd.concat(
            [
                X_tr.reset_index(drop=True),
                pd.DataFrame(tr_poly[:, new_mask], columns=new_names),
            ],
            axis=1,
        )
        X_te = pd.concat(
            [
                X_te.reset_index(drop=True),
                pd.DataFrame(te_poly[:, new_mask], columns=new_names),
            ],
            axis=1,
        )

        feature_names = list(X_tr.columns)

        # ── Replace ±inf BEFORE scaling ──────────────────────────
        X_tr = X_tr.replace([np.inf, -np.inf], np.nan).fillna(0)
        X_te = X_te.replace([np.inf, -np.inf], np.nan).fillna(0)

        # ── Scale (fit on train only) ────────────────────────────
        scaler = StandardScaler()
        X_tr_arr = scaler.fit_transform(X_tr)
        X_te_arr = scaler.transform(X_te)

        # ── Winsorize (percentiles from train only) ──────────────
        p1 = np.percentile(X_tr_arr, 1, axis=0)
        p99 = np.percentile(X_tr_arr, 99, axis=0)
        X_tr_arr = np.clip(X_tr_arr, p1, p99)
        X_te_arr = np.clip(X_te_arr, p1, p99)

        # ── Save preprocessing artifacts ─────────────────────────
        joblib.dump(scaler, self.artifacts_dir / "scaler.joblib")
        joblib.dump(medians.to_dict(), self.artifacts_dir / "imputation_medians.joblib")
        joblib.dump(poly, self.artifacts_dir / "poly_features.joblib")
        joblib.dump(
            {"p1": p1.tolist(), "p99": p99.tolist()},
            self.artifacts_dir / "winsorization_params.joblib",
        )
        joblib.dump(feature_names, self.artifacts_dir / "final_feature_names.joblib")
        print("Saved preprocessing artifacts")

        return X_tr_arr, X_te_arr, feature_names

    # ==============================================================
    #  DIAGNOSTICS
    # ==============================================================
    def _diagnose(self, X, y, feature_names):
        """Understand WHY models struggle before trying to fix them."""
        print(f"\n{'=' * 60}")
        print("  DATA QUALITY DIAGNOSTIC")
        print(f"{'=' * 60}")

        # ── Class distribution ───────────────────────────────────
        dist = y.value_counts().sort_index()
        print("\nClass distribution (training set):")
        for cls, cnt in dist.items():
            pct = cnt / len(y) * 100
            bar = "█" * int(pct)
            print(f"  Class {cls}: {cnt:6d}  ({pct:5.1f}%)  {bar}")

        ratio = dist.max() / dist.min()
        print(f"  Imbalance ratio: {ratio:.1f}:1", "[WARN]" if ratio > 3 else "[OK]")

        # ── Linear correlations ──────────────────────────────────
        n_feat = min(len(feature_names), X.shape[1])
        corrs = []
        for i in range(n_feat):
            r = np.corrcoef(X[:, i], y)[0, 1]
            if np.isfinite(r):
                corrs.append((feature_names[i], r))
        corrs.sort(key=lambda x: abs(x[1]), reverse=True)

        print(f"\nTop 10 linear correlations with target:")
        for name, r in corrs[:10]:
            bar = "█" * int(abs(r) * 80)
            print(f"  {name:40s} {r:+.4f}  {bar}")

        max_corr = max(abs(c) for _, c in corrs) if corrs else 0

        # ── Mutual information (captures non-linear) ─────────────
        print(f"\nComputing mutual information (non-linear relevance)...")
        mi = mutual_info_classif(X, y, random_state=42, n_neighbors=5)
        mi_pairs = sorted(
            [
                (feature_names[i] if i < len(feature_names) else f"f{i}", mi[i])
                for i in range(len(mi))
            ],
            key=lambda x: -x[1],
        )

        print("Top 10 features by mutual information:")
        for name, score in mi_pairs[:10]:
            bar = "█" * int(score * 300)
            print(f"  {name:40s} {score:.4f}  {bar}")

        total_mi = sum(mi)
        max_mi = max(mi)

        # ── Diagnosis ────────────────────────────────────────────
        print(f"\n{'─' * 60}")
        print(f"  Max |correlation|: {max_corr:.4f}")
        print(f"  Max MI score:      {max_mi:.4f}")
        print(f"  Total MI:          {total_mi:.4f}")

        if max_mi < 0.01:
            print("\n  🔴 CRITICAL: Features have almost NO predictive power!")
            print("     The label definition likely needs to change.")
            print("     Possible causes:")
            print("       - Labels are based on too-far-future outcomes")
            print("       - Label thresholds create arbitrary boundaries")
            print("       - Features describe current state, labels describe future")
        elif max_mi < 0.03:
            print("\n  🟡 WEAK: Limited predictive signal detected.")
            print("     Models will have modest accuracy (~0.50-0.60).")
            print("     This is NORMAL for crypto risk prediction.")
        else:
            print(f"\n  🟢 GOOD: Meaningful signal detected (MI={max_mi:.4f}).")
        print(f"{'─' * 60}")

        # ── Save diagnostic plot ─────────────────────────────────
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # MI bar chart
        top_mi = mi_pairs[:20]
        axes[0].barh(
            range(len(top_mi)),
            [s for _, s in top_mi],
            color="steelblue",
        )
        axes[0].set_yticks(range(len(top_mi)))
        axes[0].set_yticklabels([n for n, _ in top_mi], fontsize=8)
        axes[0].set_title("Mutual Information with Target")
        axes[0].invert_yaxis()

        # Class distribution
        dist.plot.bar(ax=axes[1], color=["green", "orange", "red"])
        axes[1].set_title("Class Distribution")
        axes[1].set_xlabel("Risk Label")
        axes[1].set_ylabel("Count")

        plt.tight_layout()
        plt.savefig(self.artifacts_dir / "data_diagnostic.png", dpi=150)
        plt.close()
        print("Saved data_diagnostic.png")

    # ==============================================================
    #  HYPERPARAMETER TUNING
    # ==============================================================
    def _tune_models(self, X, y, tscv, scorer):
        """
        Find optimal regularization for each model via RandomizedSearchCV.

        The search spaces span from UNDERFIT to OVERFIT so the
        best configuration lands in the sweet spot automatically.
        """
        print(f"\n{'=' * 60}")
        print("  HYPERPARAMETER SEARCH  (RandomizedSearchCV)")
        print(f"{'=' * 60}")

        configs = {
            # ── Logistic Regression ──────────────────────────────
            # Reduced from 18 to 6 configs
            "logreg": (
                LogisticRegression(
                    max_iter=5000,
                    class_weight="balanced",
                    solver="saga",
                    random_state=42,
                ),
                {
                    "C": [0.1, 0.5, 1.0],
                    "penalty": ["l2"],
                },
                3,  # was 18
            ),
            # ── Random Forest ────────────────────────────────────
            # Reduced from 80 to 12 configs
            "rf": (
                RandomForestClassifier(
                    class_weight="balanced_subsample",
                    random_state=42,
                    n_jobs=-1,
                    oob_score=True,
                ),
                {
                    "n_estimators": [300, 500],
                    "max_depth": [12, 20],
                    "min_samples_split": [5, 15],
                    "min_samples_leaf": [2, 8],
                    "max_features": ["sqrt"],
                },
                12,  # was 80
            ),
            # ── XGBoost ──────────────────────────────────────────
            # Reduced from 120 to 20 configs
            "xgb": (
                xgb.XGBClassifier(
                    objective="multi:softprob",
                    num_class=3,
                    random_state=42,
                    tree_method="hist",
                ),
                {
                    "n_estimators": [400, 600],
                    "max_depth": [5, 7],
                    "learning_rate": [0.05, 0.1],
                    "subsample": [0.7, 0.9],
                    "colsample_bytree": [0.6, 0.8],
                    "reg_alpha": [0.1, 1.0],
                    "reg_lambda": [2.0, 5.0],
                    "min_child_weight": [5, 10],
                    "gamma": [0.1, 0.5],
                },
                20,  # was 120
            ),
            # ── Gradient Boosting (sklearn) ──────────────────────
            # Reduced from 80 to 12 configs
            "gb": (
                GradientBoostingClassifier(random_state=42),
                {
                    "n_estimators": [300, 500],
                    "max_depth": [4, 6],
                    "learning_rate": [0.05, 0.1],
                    "subsample": [0.8, 1.0],
                    "min_samples_split": [10, 20],
                    "min_samples_leaf": [5, 10],
                    "max_features": ["sqrt"],
                },
                12,  # was 80
            ),
        }

        tuned = {}

        for name, (model, params, n_iter) in configs.items():
            print(f"\n  ┌─ {name.upper()} ({n_iter} random configs) ─────────")

            search = RandomizedSearchCV(
                model,
                params,
                n_iter=n_iter,
                cv=tscv,
                scoring=scorer,
                random_state=42,
                n_jobs=-1 if name not in ("xgb",) else 1,
                return_train_score=True,  # KEY: detect overfit in CV
                error_score=np.nan,  # skip broken configs
                verbose=0,
            )
            search.fit(X, y)

            # Extract CV train/val scores for best config
            res = pd.DataFrame(search.cv_results_).sort_values("rank_test_score")
            best_row = res.iloc[0]
            cv_train = best_row["mean_train_score"]
            cv_val = best_row["mean_test_score"]
            cv_gap = cv_train - cv_val

            print(f"  │  Best CV val F1  : {cv_val:.4f}")
            print(f"  │  Best CV train F1: {cv_train:.4f}  (gap: {cv_gap:+.4f})")
            print(f"  │  Best params     : {search.best_params_}")

            # Show top 5 configs to verify search explored well
            print(f"  │  Top 5 configs:")
            for _, row in res.head(5).iterrows():
                tr = row["mean_train_score"]
                va = row["mean_test_score"]
                print(f"  │    val={va:.4f}  train={tr:.4f}  gap={tr-va:+.4f}")

            # Flag if search itself shows overfit/underfit
            if cv_gap > 0.15:
                print(f"  │  [WARN] CV gap large — model may overfit")
            elif cv_val < 0.45:
                print(
                    f"  │  [WARN] CV val low — features may lack signal for this model"
                )

            print(f"  └────────────────────────────────────────────")

            tuned[name] = (
                search.best_estimator_,
                float(cv_val),
                search.best_params_,
                float(cv_train),
            )

        return tuned

    # ==============================================================
    #  PLOTTING
    # ==============================================================
    def _plot_confusion_matrix(self, cm, model_name):
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=["Low", "Medium", "High"],
            yticklabels=["Low", "Medium", "High"],
        )
        plt.title(f"Confusion Matrix – {model_name.upper()}")
        plt.ylabel("True Label")
        plt.xlabel("Predicted Label")
        plt.tight_layout()
        plt.savefig(self.artifacts_dir / f"confusion_matrix_{model_name}.png", dpi=150)
        plt.close()

    def _plot_feature_importance(self, model, model_name, feature_names):
        inner = self._get_inner_model(model)
        if inner is None:
            return

        importances = inner.feature_importances_
        top_n = min(20, len(importances))
        idx = np.argsort(importances)[::-1][:top_n]

        labels = [
            feature_names[i] if i < len(feature_names) else f"feat_{i}" for i in idx
        ]

        plt.figure(figsize=(10, 8))
        plt.title(f"Top {top_n} Features – {model_name.upper()}")
        plt.barh(range(top_n), importances[idx], color="steelblue")
        plt.yticks(range(top_n), labels, fontsize=9)
        plt.xlabel("Importance")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(
            self.artifacts_dir / f"feature_importance_{model_name}.png", dpi=150
        )
        plt.close()
        print(f"  Saved feature_importance_{model_name}.png")

    @staticmethod
    def _get_inner_model(model):
        """Unwrap EpsilonCalibratedClassifier to get the real model."""
        for attr in ("base_model", "estimator", "model"):
            if hasattr(model, attr):
                inner = getattr(model, attr)
                if hasattr(inner, "feature_importances_"):
                    return inner
                # One more level (CalibratedClassifierCV wraps)
                for attr2 in ("base_model", "estimator"):
                    if hasattr(inner, attr2):
                        deep = getattr(inner, attr2)
                        if hasattr(deep, "feature_importances_"):
                            return deep
        if hasattr(model, "feature_importances_"):
            return model
        return None


def main():
    trainer = RiskClassifierTrainer()
    trainer.run()


if __name__ == "__main__":
    main()

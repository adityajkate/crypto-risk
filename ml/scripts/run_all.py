#!/usr/bin/env python3
"""
Full training pipeline runner.
Executes all training scripts in sequence.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    ("Data Collection", "training/collect_training_data.py"),
    ("Preprocessing", "training/preprocess.py"),
    ("Label Generation", "training/label_generator.py"),
    ("Risk Classifier", "training/train_risk_classifier.py"),
    ("Volatility Regression", "training/train_regression.py"),
    ("Clustering", "training/train_clustering.py"),
    ("Regime Detection", "training/train_regime_model.py"),
    ("PCA", "training/run_pca.py"),
]


def run_step(name: str, script: str) -> bool:
    """Run a training step."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")

    result = subprocess.run([sys.executable, script], cwd=Path(__file__).parent.parent)

    if result.returncode != 0:
        print(f"ERROR: {name} failed with code {result.returncode}")
        return False

    print(f"✓ {name} completed successfully")
    return True


def main():
    """Run complete training pipeline."""
    print("Starting Crypto Risk Lens Training Pipeline")
    print(f"{'='*60}")

    for name, script in SCRIPTS:
        if not run_step(name, script):
            print(f"\nPipeline failed at: {name}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print("Training pipeline completed successfully!")
    print(f"{'='*60}")
    print("\nGenerated artifacts:")

    artifacts_dir = Path(__file__).parent.parent.parent / "models"
    for artifact in sorted(artifacts_dir.glob("*.joblib")):
        print(f"  - {artifact.name}")


if __name__ == "__main__":
    main()

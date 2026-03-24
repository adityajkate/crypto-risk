"""Shared model classes used by both training and inference."""
import numpy as np


class EpsilonCalibratedClassifier:
    """Wrapper that applies an epsilon probability floor to a calibrated classifier.

    Pickle-safe: handles both the current serialisation format and the legacy
    format where CalibratedClassifierCV attributes were stored directly in this
    wrapper's __dict__.
    """

    _SKLEARN_CALIBRATED_KEYS = frozenset([
        "estimator", "method", "cv", "n_jobs", "ensemble",
        "calibrated_classifiers_", "classes_", "n_features_in_", "_sklearn_version"
    ])

    def __init__(self, calibrated_model, epsilon=1e-4):
        object.__setattr__(self, "calibrated_model", calibrated_model)
        object.__setattr__(self, "epsilon", epsilon)

    def __getstate__(self):
        return {"calibrated_model": self.calibrated_model, "epsilon": self.epsilon}

    def __setstate__(self, state):
        if "calibrated_model" in state:
            object.__setattr__(self, "calibrated_model", state["calibrated_model"])
            object.__setattr__(self, "epsilon", state.get("epsilon", 1e-4))
        elif self._SKLEARN_CALIBRATED_KEYS & set(state.keys()):
            from sklearn.calibration import CalibratedClassifierCV
            inner = object.__new__(CalibratedClassifierCV)
            inner.__setstate__(state)
            object.__setattr__(self, "calibrated_model", inner)
            object.__setattr__(self, "epsilon", 1e-4)
        else:
            raise ValueError(
                f"Cannot deserialize EpsilonCalibratedClassifier: "
                f"unrecognised state keys {list(state.keys())}"
            )

    def predict(self, X):
        return self.calibrated_model.predict(X)

    def predict_proba(self, X):
        """Apply epsilon floor and re-normalize probabilities."""
        proba = self.calibrated_model.predict_proba(X)
        proba = np.maximum(proba, self.epsilon)
        proba = proba / proba.sum(axis=1, keepdims=True)
        return proba

    def __getattr__(self, name):
        inner = self.__dict__.get("calibrated_model")
        if inner is None:
            raise AttributeError(name)
        return getattr(inner, name)

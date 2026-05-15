from __future__ import annotations

from pathlib import Path
import pickle
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class MLAnomalyDetector:
    """Simple anomaly detector built on IsolationForest.

    Designed to work out-of-the-box on LAUNCH X431 CSV exports where many
    columns may be non-numeric. Non-numeric columns are ignored. The model
    uses z-scored numeric features.
    """

    def __init__(self, n_estimators: int = 200, contamination: float = 0.1, random_state: int = 42,
                 use_deep_learning: bool = False) -> None:
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.use_deep_learning = use_deep_learning  # placeholder flag

        self._scaler: Optional[StandardScaler] = None
        self._model: Optional[IsolationForest] = None
        self._fitted: bool = False

    def _select_numeric(self, data: pd.DataFrame) -> pd.DataFrame:
        clean = data.copy()
        # Coerce to numeric
        for col in clean.columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce")
        numeric = clean.select_dtypes(include=[np.number])
        # Drop obvious counters/indices if present
        for drop_col in ("Row", "Num"):
            if drop_col in numeric.columns:
                numeric = numeric.drop(columns=[drop_col])
        if numeric.empty:
            return numeric
        # Keep columns that have sufficient non-null coverage
        coverage = numeric.notna().mean(axis=0)
        keep_cols = [c for c, r in coverage.items() if r >= 0.01]
        numeric = numeric[keep_cols]
        # Drop rows that are entirely NaN after pruning
        numeric = numeric.dropna(how="all")
        return numeric

    def fit(self, data: pd.DataFrame) -> None:
        X = self._select_numeric(data)
        if X.empty:
            raise ValueError("No numeric data available to fit the model.")

        self._scaler = StandardScaler()
        Xs = self._scaler.fit_transform(X.values)

        self._model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self._model.fit(Xs)
        self._fitted = True

    def _require_fitted(self) -> None:
        if not self._fitted or self._model is None or self._scaler is None:
            raise RuntimeError("Detector is not fitted. Call fit() first.")

    def predict(self, data: pd.DataFrame) -> np.ndarray:
        self._require_fitted()
        X = self._select_numeric(data)
        Xs = self._scaler.transform(X.values)
        return self._model.predict(Xs)

    def predict_proba(self, data: pd.DataFrame) -> np.ndarray:
        self._require_fitted()
        X = self._select_numeric(data)
        Xs = self._scaler.transform(X.values)
        scores = -self._model.score_samples(Xs)  # higher => more anomalous
        # Min-max normalize to [0,1]
        min_s, max_s = float(scores.min()), float(scores.max())
        if max_s == min_s:
            return np.zeros_like(scores)
        return (scores - min_s) / (max_s - min_s)

    def detect_head_gasket_failure(self, data: pd.DataFrame) -> Dict[str, Any]:
        self._require_fitted()
        proba = self.predict_proba(data)
        mean_anom = float(np.mean(proba)) if proba.size > 0 else 0.0

        verdict = "NO CLEAR HEAD GASKET FAILURE"
        confidence = min(max(mean_anom, 0.0), 1.0)
        if mean_anom > 0.5:
            verdict = "POSSIBLE HEAD GASKET ISSUE"

        return {
            "verdict": verdict,
            "confidence": confidence,
        }

    def save(self, path: Path | str) -> None:
        self._require_fitted()
        obj = {
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "scaler": self._scaler,
            "model": self._model,
            "use_deep_learning": self.use_deep_learning,
        }
        with open(Path(path), "wb") as f:
            pickle.dump(obj, f)

    @classmethod
    def load(cls, path: Path | str) -> "MLAnomalyDetector":
        with open(Path(path), "rb") as f:
            obj = pickle.load(f)
        det = cls(
            n_estimators=obj["n_estimators"],
            contamination=obj["contamination"],
            random_state=obj["random_state"],
            use_deep_learning=obj.get("use_deep_learning", False),
        )
        det._scaler = obj["scaler"]
        det._model = obj["model"]
        det._fitted = True
        return det



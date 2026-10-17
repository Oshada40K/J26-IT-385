"""The trained behavioural text trait estimator: one feature union + one classifier per trait."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

from . import TRAITS
from .features import to_matrix


def make_classifier(C: float, seed: int) -> LogisticRegression:
    # Linear model: strong on TF-IDF, fast, and gives exact linear SHAP values later.
    return LogisticRegression(C=C, solver="liblinear", class_weight="balanced",
                              max_iter=5000, random_state=seed)


@dataclass
class TextTraitModel:
    """T_beh text estimator. ``predict_proba`` returns P(high trait) in [0, 1] per trait."""

    blocks: list[str]
    features: FeatureUnion
    classifiers: dict[str, LogisticRegression]
    metadata: dict = field(default_factory=dict)
    regressors: dict = field(default_factory=dict)  # optional: trait -> Ridge on percentile/100

    def predict_score(self, texts) -> pd.DataFrame:
        """Continuous trait estimate on the 0-100 percentile scale (needs regressors)."""
        if not self.regressors:
            raise ValueError("This model was trained without regressors.")
        X = self.transform(texts)
        return pd.DataFrame({t: np.clip(self.regressors[t].predict(X), 0, 1) * 100 for t in TRAITS})

    def transform(self, texts) -> object:
        return to_matrix(self.features.transform(list(texts)))

    def predict_proba(self, texts) -> pd.DataFrame:
        X = self.transform(texts)
        return pd.DataFrame({t: self.classifiers[t].predict_proba(X)[:, 1] for t in TRAITS})

    def predict(self, texts) -> pd.DataFrame:
        return (self.predict_proba(texts) >= 0.5).astype(int)

    def feature_names(self) -> np.ndarray:
        return self.features.get_feature_names_out()

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: str | Path) -> "TextTraitModel":
        return joblib.load(path)

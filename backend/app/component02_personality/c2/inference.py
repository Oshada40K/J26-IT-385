"""Load the trained text trait model and score student text (for the backend / API).

Example:
    from c2.inference import TextTraitPredictor
    predictor = TextTraitPredictor("models/text_trait_model.joblib")
    predictor.predict(["When my team disagrees I listen first, then suggest a plan."])
    # -> {"OPN": 0.61, "CON": 0.55, "EXT": 0.48, "AGR": 0.66, "NEU": 0.39}

Values are P(high trait) in [0, 1]: the T_beh (text) estimate used by the fusion step.
The first call downloads the Sentence-BERT model (all-mpnet-base-v2, ~420 MB) once and
caches it in the Hugging Face cache folder; later calls are offline and fast.
"""
from __future__ import annotations

from pathlib import Path

from . import TRAITS
from .text_model import TextTraitModel


class TextTraitPredictor:
    def __init__(self, model_path: str | Path, device: str | None = None):
        self.model = TextTraitModel.load(model_path)
        for name, block in self.model.features.transformer_list:
            if name == "sbert":
                block.cache_dir = ""      # no on-disk embedding cache when serving
                block.device = device     # None = GPU if available, else CPU
        self.blocks = self.model.blocks

    def predict(self, responses: list[str] | str) -> dict[str, float]:
        """Score ONE student. Several open-ended answers are joined into one text."""
        text = responses if isinstance(responses, str) else " ".join(r.strip() for r in responses if r)
        if len(text.split()) < 20:
            raise ValueError("Need at least 20 words of free text for a reliable estimate.")
        probs = self.model.predict_proba([text]).iloc[0]
        return {t: round(float(probs[t]), 4) for t in TRAITS}

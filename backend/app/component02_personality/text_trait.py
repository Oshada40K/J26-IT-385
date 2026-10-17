import os, sys, warnings
from functools import lru_cache
from pathlib import Path

from sklearn.exceptions import InconsistentVersionWarning

# 1. Make the saved model find its code (it was saved expecting a package named "c2")
from . import c2 as _c2
from .c2 import features as _f, lexicons as _lx, text_model as _tm
sys.modules.setdefault("c2", _c2)
sys.modules.setdefault("c2.features", _f)
sys.modules.setdefault("c2.lexicons", _lx)
sys.modules.setdefault("c2.text_model", _tm)

from .c2.inference import TextTraitPredictor

MODEL_PATH = Path(__file__).parent / "text_model_output" / "text_trait_model.joblib"

# 2. Load the model only once, then reuse it
@lru_cache(maxsize=1)
def get_predictor() -> TextTraitPredictor:
    # The model was saved with scikit-learn 1.6.1; the shared backend runs 1.5.2.
    # version_check/report.md shows both give identical predictions, so only this
    # warning is hidden, and only while the model loads. Re-run the check if versions change.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
        p = TextTraitPredictor(MODEL_PATH)
    # 3. Optional: use a local Sentence-BERT folder instead of downloading it
    local_sbert = os.getenv("PERSONALITY_SBERT_MODEL_PATH")
    if local_sbert:
        for name, block in p.model.features.transformer_list:
            if name == "sbert":
                block.model_name = local_sbert
    return p
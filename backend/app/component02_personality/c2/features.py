"""Feature blocks for the behavioural text trait estimators.

Three blocks, each an sklearn transformer that takes a list of raw texts:

* ``tfidf`` - sparse lexical features (word 1-2 grams). Interpretable.
* ``sbert`` - dense semantic features (Sentence-BERT, mean-pooled over chunks).
* ``psy``   - a few dozen named psycholinguistic features. Interpretable.

All blocks are label-independent, so fitting them is unsupervised. They are
still fitted only on training folds, so no vocabulary or scaling statistics
leak from validation or held-out data.

Every block exposes ``get_feature_names_out`` with a ``block__`` prefix so SHAP
attributions can later be aggregated back to blocks and named features.
"""
from __future__ import annotations

import hashlib
import math
import pickle
import re
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import StandardScaler

from .lexicons import CATEGORIES

TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
SENT_RE = re.compile(r"[.!?]+")


# --------------------------------------------------------------------------- TF-IDF
class TfidfBlock(BaseEstimator, TransformerMixin):
    """Word 1-2 gram TF-IDF. Keeps 1-letter tokens such as "i" and keeps stopwords."""

    def __init__(self, ngram_range=(1, 2), min_df=3, max_df=0.9, max_features=30000,
                 sublinear_tf=True, weight=1.0):
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        self.max_features = max_features
        self.sublinear_tf = sublinear_tf
        self.weight = weight

    def fit(self, X, y=None):
        self.vec_ = TfidfVectorizer(
            lowercase=True, ngram_range=tuple(self.ngram_range), min_df=self.min_df,
            max_df=self.max_df, max_features=self.max_features, sublinear_tf=self.sublinear_tf,
            token_pattern=r"(?u)\b\w[\w']*\b", dtype=np.float32,
        )
        self.vec_.fit(X)
        return self

    def transform(self, X):
        return self.vec_.transform(X) * self.weight  # rows are L2-normalised (norm = weight)

    def get_feature_names_out(self, input_features=None):
        return np.array(["tfidf__" + f for f in self.vec_.get_feature_names_out()])


# --------------------------------------------------------------------------- Psycholinguistic
def psy_feature_dict(text: str) -> dict[str, float]:
    lower = text.lower()
    tokens = TOKEN_RE.findall(lower)
    n = max(len(tokens), 1)
    sentences = [s for s in SENT_RE.split(text) if s.strip()]
    feats = {
        "log_word_count": math.log1p(len(tokens)),
        "mean_word_length": float(np.mean([len(t) for t in tokens])) if tokens else 0.0,
        "mean_sentence_length": n / max(len(sentences), 1),
        # type-token ratio on a fixed window so it does not just track essay length
        "type_token_ratio": len(set(tokens[:300])) / max(min(n, 300), 1),
        "long_word_ratio": sum(len(t) > 6 for t in tokens) / n,
        "exclamation_rate": lower.count("!") / n,
        "question_rate": lower.count("?") / n,
    }
    counts = {name: 0 for name in CATEGORIES}
    for tok in tokens:
        for name, words in CATEGORIES.items():
            if tok in words:
                counts[name] += 1
    for name, c in counts.items():
        feats[f"{name}_ratio"] = c / n
    return feats


PSY_FEATURE_NAMES = list(psy_feature_dict("A placeholder sentence.").keys())


class PsycholinguisticBlock(BaseEstimator, TransformerMixin):
    """Named, standardised psycholinguistic features.

    After standardising, the block is divided by sqrt(n_features) so its row norm
    is about 1, comparable to the L2-normalised TF-IDF and SBERT blocks.
    """

    def __init__(self, weight=1.0):
        self.weight = weight

    def _raw(self, X):
        return np.array([[psy_feature_dict(t)[k] for k in PSY_FEATURE_NAMES] for t in X],
                        dtype=np.float64)

    def fit(self, X, y=None):
        self.scaler_ = StandardScaler().fit(self._raw(X))
        return self

    def transform(self, X):
        Z = self.scaler_.transform(self._raw(X))
        return (Z * (self.weight / math.sqrt(Z.shape[1]))).astype(np.float32)

    def get_feature_names_out(self, input_features=None):
        return np.array(["psy__" + f for f in PSY_FEATURE_NAMES])


# --------------------------------------------------------------------------- Sentence-BERT
def chunk_words(text: str, size: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]


class SbertBlock(BaseEstimator, TransformerMixin):
    """Sentence-BERT document embeddings.

    MiniLM-style models truncate at ~256 word pieces, but essays are ~650 words,
    so each text is split into word windows, each window is embedded, and the
    windows are mean-pooled into one L2-normalised document vector.

    Embeddings are cached on disk (keyed by model, chunk size and text hash),
    so repeated CV folds and ablation runs only encode each text once.
    """

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2", chunk_size=180,
                 batch_size=32, cache_dir="data/cache", device=None, weight=1.0):
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.batch_size = batch_size
        self.cache_dir = cache_dir
        self.device = device
        self.weight = weight

    # the loaded model is never pickled with the saved estimator
    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("_model", None)
        state.pop("_cache", None)
        return state

    def _cache_path(self) -> Path | None:
        if not self.cache_dir:
            return None
        safe = re.sub(r"[^A-Za-z0-9]+", "_", self.model_name)
        return Path(self.cache_dir) / f"sbert_{safe}_c{self.chunk_size}.pkl"

    def _load_cache(self) -> dict:
        if getattr(self, "_cache", None) is None:
            p = self._cache_path()
            self._cache = pickle.loads(p.read_bytes()) if p and p.exists() else {}
        return self._cache

    def _save_cache(self):
        p = self._cache_path()
        if p:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(pickle.dumps(self._cache))

    def _get_model(self):
        if getattr(self, "_model", None) is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:  # pragma: no cover - depends on environment
                raise ImportError(
                    "The 'sbert' block needs sentence-transformers: pip install sentence-transformers"
                ) from e
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def _encode_chunks(self, chunks: list[str]) -> np.ndarray:
        """Encode text chunks into L2-normalised vectors (patched in unit tests)."""
        return self._get_model().encode(
            chunks, batch_size=self.batch_size, normalize_embeddings=True,
            show_progress_bar=len(chunks) > 500, convert_to_numpy=True,
        )

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def embed(self, X) -> np.ndarray:
        cache = self._load_cache()
        texts = list(X)
        todo = [t for t in dict.fromkeys(texts) if self._key(t) not in cache]
        if todo:
            chunks, owner = [], []
            for i, t in enumerate(todo):
                cs = chunk_words(t, self.chunk_size)
                chunks.extend(cs)
                owner.extend([i] * len(cs))
            vecs = np.asarray(self._encode_chunks(chunks), dtype=np.float32)
            owner = np.array(owner)
            for i, t in enumerate(todo):
                v = vecs[owner == i].mean(axis=0)
                cache[self._key(t)] = v / (np.linalg.norm(v) + 1e-12)
            self._save_cache()
        return np.vstack([cache[self._key(t)] for t in texts]).astype(np.float32)

    def fit(self, X, y=None):
        self.dim_ = self.embed(X[:1]).shape[1]
        return self

    def transform(self, X):
        return self.embed(X) * self.weight

    def get_feature_names_out(self, input_features=None):
        return np.array([f"sbert__dim{i:03d}" for i in range(self.dim_)])


# --------------------------------------------------------------------------- assembly
BLOCKS = ("tfidf", "sbert", "psy")


def build_features(blocks, cfg: dict) -> FeatureUnion:
    """Create the FeatureUnion for the requested blocks (e.g. ["tfidf", "psy"])."""
    weights = cfg.get("block_weights", {})
    parts = []
    for b in blocks:
        if b == "tfidf":
            parts.append(("tfidf", TfidfBlock(**cfg.get("tfidf", {}), weight=weights.get(b, 1.0))))
        elif b == "sbert":
            parts.append(("sbert", SbertBlock(**cfg.get("sbert", {}), weight=weights.get(b, 1.0))))
        elif b == "psy":
            parts.append(("psy", PsycholinguisticBlock(weight=weights.get(b, 1.0))))
        else:
            raise ValueError(f"Unknown feature block '{b}'. Choose from {BLOCKS}.")
    if not parts:
        raise ValueError("At least one feature block is required.")
    # verbose_feature_names_out=False: our blocks already prefix their names
    return FeatureUnion(parts, verbose_feature_names_out=False)


def to_matrix(X):
    """FeatureUnion returns sparse if any block is sparse; keep CSR for fast fitting."""
    return X.tocsr() if sparse.issparse(X) else X

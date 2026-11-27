"""Semantic embedding and cosine similarity matching (SBERT primary, TF-IDF cosine fallback)."""
import os
from threading import Lock
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from ..config import MODEL_NAME

MODEL_LOCK = Lock()
_SBERT_CACHE = {}


def load_sbert_model():
    """Load SentenceTransformer only when available and enabled."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(
        os.getenv('SKILL_SBERT_MODEL_PATH', MODEL_NAME),
        local_files_only=True,
        trust_remote_code=False,
    )


def sbert_enabled() -> bool:
    return os.getenv('SKILL_ENABLE_SBERT', 'false').lower() == 'true'


class SemanticMatcher:
    """Computes cosine similarity over SBERT embeddings when available, or TF-IDF n-gram vectors."""

    def __init__(self, items: list[dict], sbert_loader=None):
        self.items = [item for item in items if item.get('canonical_name')]
        self.texts = [
            f"{item['canonical_name']}. {item.get('description', '')}".strip()
            for item in self.items
        ]
        self.backend = 'tfidf_cosine_fallback'
        self.sbert_model = None
        self.vectorizer = None
        self.matrix = None

        if not self.items:
            return

        if sbert_enabled():
            try:
                loader = sbert_loader or load_sbert_model
                with MODEL_LOCK:
                    model = loader()
                    vectors = model.encode(self.texts, normalize_embeddings=True)
                self.matrix = np.asarray(vectors, dtype=np.float32)
                self.sbert_model = model
                self.backend = MODEL_NAME
                return
            except Exception:
                # Fall back cleanly to lightweight TF-IDF cosine similarity when SBERT is unavailable.
                self.sbert_model = None

        # Character + word n-grams capture morphological variants and multi-word semantic overlap.
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(3, 5),
            lowercase=True,
            sublinear_tf=True,
            max_features=20000,
            dtype=np.float32,
        )
        self.matrix = self.vectorizer.fit_transform(self.texts)

    def match_phrase(self, phrase: str, threshold: float | None = None) -> tuple[dict | None, float, str]:
        if not self.items or self.matrix is None or not phrase or not phrase.strip():
            return None, 0.0, self.backend

        effective_threshold = threshold if threshold is not None else (0.65 if self.sbert_model is not None else 0.72)

        if self.sbert_model is not None:
            with MODEL_LOCK:
                q_vec = np.asarray(self.sbert_model.encode([phrase], normalize_embeddings=True), dtype=np.float32)
            sims = (self.matrix @ q_vec[0]).ravel()
        else:
            q_vec = self.vectorizer.transform([phrase])
            sims = (self.matrix @ q_vec.T).toarray().ravel()

        if len(sims) == 0:
            return None, 0.0, self.backend
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])
        if best_score >= effective_threshold:
            matched = self.items[best_idx]
            # Avoid noisy single-word char-ngram collisions (e.g. "MATLAB" -> "pMatlab") when SBERT is not used.
            if self.sbert_model is None and ' ' not in phrase.strip() and ' ' not in matched['canonical_name'].strip():
                if matched['canonical_name'].casefold() != phrase.strip().casefold():
                    return None, round(best_score, 4), self.backend
            return matched, round(best_score, 4), self.backend
        return None, round(best_score, 4), self.backend

    def score_texts(self, query_text: str, candidate_texts: list[str]) -> list[float]:
        if not candidate_texts or not query_text:
            return []
        if self.sbert_model is not None:
            with MODEL_LOCK:
                vectors = np.asarray(
                    self.sbert_model.encode([query_text, *candidate_texts], normalize_embeddings=True),
                    dtype=np.float32,
                )
            return [round(float(vectors[0] @ vectors[i]), 4) for i in range(1, len(vectors))]

        vec = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        mat = vec.fit_transform([query_text, *candidate_texts])
        sims = (mat[1:] @ mat[0].T).toarray().ravel()
        return [round(float(s), 4) for s in sims]

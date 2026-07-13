import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from config import EMBED_BATCH_SIZE, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class Embedder:
    """Thin wrapper around EmbeddingGemma via sentence-transformers."""

    def __init__(self, model_id: str = EMBEDDING_MODEL):
        self.model_id = model_id
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading embedding model: %s", self.model_id)
            self._model = SentenceTransformer(self.model_id)
            logger.info("Model loaded on device: %s", self._model.device)
        return self._model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(
            texts,
            prompt_name="Retrieval-document",
            batch_size=EMBED_BATCH_SIZE,
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True,
        )
        return _normalize(vectors)

    def embed_query(self, query: str) -> np.ndarray:
        vector = self.model.encode(
            query,
            prompt_name="Retrieval-query",
            convert_to_numpy=True,
        )
        return _normalize(vector)


def _normalize(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize so dot product equals cosine similarity."""
    if vectors.ndim == 1:
        norm = np.linalg.norm(vectors)
        return vectors / norm if norm > 0 else vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return vectors / norms

import hashlib
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from chunker import chunk_manim_kb
from config import DOCS_PATH, EMBEDDING_MODEL, INDEX_PATH
from embedder import Embedder

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    chunk: dict
    score: float


class VectorIndex:
    def __init__(self, chunks: list[dict], vectors: np.ndarray, model_id: str):
        self.chunks = chunks
        self.vectors = vectors
        self.model_id = model_id

    def search(
        self,
        query: str,
        embedder: Embedder,
        top_k: int = 5,
        chunk_type: str | None = None,
    ) -> list[SearchResult]:
        query_vec = embedder.embed_query(query)

        if chunk_type:
            indices = [
                i for i, c in enumerate(self.chunks) if c["chunk_type"] == chunk_type
            ]
            if not indices:
                return []
            sub_vectors = self.vectors[indices]
            scores = sub_vectors @ query_vec
            ranked = np.argsort(scores)[::-1][:top_k]
            return [
                SearchResult(chunk=self.chunks[indices[i]], score=float(scores[i]))
                for i in ranked
            ]

        scores = self.vectors @ query_vec
        ranked = np.argsort(scores)[::-1][:top_k]
        return [
            SearchResult(chunk=self.chunks[i], score=float(scores[i]))
            for i in ranked
        ]


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_cache_valid(cache: dict, docs_path: Path, model_id: str) -> bool:
    if cache.get("model_id") != model_id:
        return False
    if cache.get("source_path") != str(docs_path):
        return False
    if not docs_path.exists():
        return False
    return (
        cache.get("source_hash") == _file_hash(docs_path)
        and cache.get("source_mtime") == docs_path.stat().st_mtime
    )


def build_index(chunks: list[dict], embedder: Embedder) -> VectorIndex:
    texts = [c.get("embed_text", c["text"]) for c in chunks]
    logger.info("Embedding %d chunks...", len(texts))
    vectors = embedder.embed_documents(texts)
    return VectorIndex(chunks=chunks, vectors=vectors, model_id=embedder.model_id)


def save_index(index: VectorIndex, path: Path, docs_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "model_id": index.model_id,
        "source_path": str(docs_path),
        "source_mtime": docs_path.stat().st_mtime,
        "source_hash": _file_hash(docs_path),
        "chunks": index.chunks,
        "vectors": index.vectors,
    }
    with open(path, "wb") as f:
        pickle.dump(data, f)
    logger.info("Index saved to %s", path)


def load_index(path: Path) -> VectorIndex | None:
    if not path.exists():
        return None
    with open(path, "rb") as f:
        data = pickle.load(f)
    return VectorIndex(
        chunks=data["chunks"],
        vectors=data["vectors"],
        model_id=data["model_id"],
    )


def get_or_build_index(
    docs_path: Path = DOCS_PATH,
    index_path: Path = INDEX_PATH,
    model_id: str = EMBEDDING_MODEL,
) -> tuple[VectorIndex, Embedder, bool]:
    """Return (index, embedder, from_cache). Rebuilds if cache is stale."""
    embedder = Embedder(model_id=model_id)

    if index_path.exists():
        with open(index_path, "rb") as f:
            cache = pickle.load(f)
        if _is_cache_valid(cache, docs_path, model_id):
            logger.info(
                "Loaded cached index: %d chunks from %s",
                len(cache["chunks"]),
                index_path,
            )
            index = VectorIndex(
                chunks=cache["chunks"],
                vectors=cache["vectors"],
                model_id=cache["model_id"],
            )
            return index, embedder, True

    if not docs_path.exists():
        raise FileNotFoundError(f"Manim KB not found: {docs_path}")

    logger.info("Building index from %s", docs_path)
    chunks = chunk_manim_kb(docs_path)
    entry_count = sum(1 for c in chunks if c["chunk_type"] == "entry")
    sig_count = sum(1 for c in chunks if c["chunk_type"] == "signature")
    logger.info("Chunked: %d entries, %d signatures", entry_count, sig_count)

    index = build_index(chunks, embedder)
    save_index(index, index_path, docs_path)
    return index, embedder, False

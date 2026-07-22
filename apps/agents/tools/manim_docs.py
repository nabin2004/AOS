from __future__ import annotations
from typing import Callable

_index = None
_embedder = None
_SEARCH_TOP_K = 5


def _get_index():
    """Lazy-load index + embedder on first search (avoids slow import)."""
    global _index, _embedder, _SEARCH_TOP_K
    if _index is None:
        from config import SEARCH_TOP_K
        from vector_index import get_or_build_index

        _SEARCH_TOP_K = SEARCH_TOP_K
        _index, _embedder, _ = get_or_build_index()
    return _index, _embedder


def _format_results(results, label: str) -> str:
    if not results:
        return f"No matching {label} found in the Manim knowledge base."

    parts: list[str] = []
    for i, hit in enumerate(results, 1):
        chunk = hit.chunk
        header = (
            f"### Result {i} (score: {hit.score:.3f})\n"
            f"- **Section:** {chunk.get('section', '')}\n"
            f"- **Name:** {chunk.get('name', '')}\n"
            f"- **Module:** {chunk.get('module', '')}\n"
        )
        if chunk.get("parent"):
            header += f"- **Parent:** {chunk['parent']}\n"
        if chunk.get("signature"):
            header += f"- **Signature:** `{chunk['signature']}`\n"

        body = chunk.get("text", "")
        parts.append(f"{header}\n{body}")

    return "\n\n---\n\n".join(parts)


def search_manim_docs(query: str, top_k: int = _SEARCH_TOP_K) -> str:
    """Semantic search over Manim API docs (classes, functions, colors)."""
    query = query.strip()
    if not query:
        return "Error: empty search query."

    index, embedder = _get_index()
    results = index.search(query, embedder, top_k=top_k, chunk_type="entry")
    return _format_results(results, "entries")


def search_manim_signatures(query: str, top_k: int = _SEARCH_TOP_K) -> str:
    """Search Manim constructors/methods for argument names and types."""
    query = query.strip()
    if not query:
        return "Error: empty search query."

    index, embedder = _get_index()
    results = index.search(query, embedder, top_k=top_k, chunk_type="signature")
    return _format_results(results, "signatures")


def manim_doc_rag() -> list[Callable[..., str]]:
    """Returns RAG tools for Manim documentation."""
    return [search_manim_docs, search_manim_signatures]

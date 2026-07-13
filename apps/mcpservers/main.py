import logging

from fastmcp import FastMCP

from config import SEARCH_TOP_K
from vector_index import SearchResult, get_or_build_index

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

server = FastMCP("Manim Docs MCP Server")

index, embedder, from_cache = get_or_build_index()
entry_count = sum(1 for c in index.chunks if c["chunk_type"] == "entry")
sig_count = sum(1 for c in index.chunks if c["chunk_type"] == "signature")
logger.info(
    "Ready: %d entries, %d signatures (cache=%s)",
    entry_count,
    sig_count,
    from_cache,
)


def _format_results(results: list[SearchResult], label: str) -> str:
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


@server.tool()
async def search_manim_kb(query: str, top_k: int = SEARCH_TOP_K) -> str:
    """
    Semantic search over Manim API documentation.
    Returns matching class, function, color, and constant entries.
    Use this to find how to use Manim APIs when writing code.
    """
    results = index.search(query, embedder, top_k=top_k, chunk_type="entry")
    return _format_results(results, "entries")


@server.tool()
async def search_manim_signatures(query: str, top_k: int = SEARCH_TOP_K) -> str:
    """
    Find Manim constructors, methods, and function signatures by semantic similarity.
    Use this to look up argument names, types, and default values.
    """
    results = index.search(query, embedder, top_k=top_k, chunk_type="signature")
    return _format_results(results, "signatures")


if __name__ == "__main__":
    server.run()

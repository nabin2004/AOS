"""manim-dsa: algorithms & data-structures visualizers."""

from __future__ import annotations

from manim_dsa import concepts as _concepts  # noqa: F401
from manim_dsa.registry import domains, get_concept, list_concepts, register_concept, stub_concept

stub_concept(id="dijkstra", domain="dsa", chapter="3.1", title="Dijkstra", tags=["graph"])
stub_concept(id="avl", domain="dsa", chapter="3.2", title="AVL Tree", tags=["tree"])
stub_concept(id="heap", domain="dsa", chapter="3.3", title="Heap", tags=["tree"])
stub_concept(id="dp_table", domain="dsa", chapter="3.4", title="DP Table", tags=["dp"])

__all__ = [
    "domains",
    "get_concept",
    "list_concepts",
    "register_concept",
    "stub_concept",
]

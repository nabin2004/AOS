"""manim-math: mathematics curriculum visualizers."""

from __future__ import annotations

from manim_math import concepts as _concepts  # noqa: F401
from manim_math.registry import domains, get_concept, list_concepts, register_concept, stub_concept

stub_concept(id="series", domain="math", chapter="3.1", title="Series", tags=["calculus"])
stub_concept(id="complex_plane", domain="math", chapter="3.2", title="Complex Plane", tags=["complex"])

__all__ = [
    "domains",
    "get_concept",
    "list_concepts",
    "register_concept",
    "stub_concept",
]

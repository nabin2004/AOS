"""manim-physics: high-school mechanics visualizers."""

from __future__ import annotations

from manim_physics import concepts as _concepts  # noqa: F401
from manim_physics.registry import domains, get_concept, list_concepts, register_concept, stub_concept

__all__ = [
    "domains",
    "get_concept",
    "list_concepts",
    "register_concept",
    "stub_concept",
]

"""manim-ai: Dive into Deep Learning curriculum visualizers for Manim."""

from __future__ import annotations

from manim_ai import (  # noqa: F401 — populate registry
    advanced,
    convolutional,
    experiments,
    fundamentals,
    neural_networks,
    optimization,
    recurrent,
    transformers,
)
from manim_ai import compute  # noqa: F401
from manim_ai.core import (
    AIIntent,
    AITheme,
    DEFAULT_THEME,
    ConceptCard,
    domains,
    get_concept,
    list_concepts,
    narrate_steps,
    register_concept,
    reveal_with_bookmarks,
    stub_concept,
)
from manim_ai.neural_networks import LinearLayer, Network

__all__ = [
    "AIIntent",
    "AITheme",
    "ConceptCard",
    "DEFAULT_THEME",
    "LinearLayer",
    "Network",
    "compute",
    "domains",
    "get_concept",
    "list_concepts",
    "narrate_steps",
    "register_concept",
    "reveal_with_bookmarks",
    "stub_concept",
]

"""manim_ai.core public surface."""

from manim_ai.core.base import AIIntent, ConceptCard, stub_concept
from manim_ai.core.registry import domains, get_concept, list_concepts, register_concept
from manim_ai.core.theme import AITheme, DEFAULT_THEME
from manim_ai.core.voiceover import narrate_steps, reveal_with_bookmarks

__all__ = [
    "AIIntent",
    "AITheme",
    "ConceptCard",
    "DEFAULT_THEME",
    "domains",
    "get_concept",
    "list_concepts",
    "narrate_steps",
    "register_concept",
    "reveal_with_bookmarks",
    "stub_concept",
]

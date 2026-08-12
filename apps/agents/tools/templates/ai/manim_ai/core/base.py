"""Base helpers and intent schema for manim-ai."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from manim import VGroup

from manim_ai.core.theme import AITheme, DEFAULT_THEME


Depth = Literal["beginner", "intermediate", "advanced"]


@dataclass
class AIIntent:
    """Thin intent payload for agent routing (not a runtime UI)."""

    domain: str
    concept: str
    parameters: dict[str, Any] = field(default_factory=dict)
    show_math: bool = True
    show_code: bool = False
    depth: Depth = "intermediate"
    narration: bool = True


class ConceptCard(VGroup):
    """Title + body group used by skeleton / stub visualizers."""

    def __init__(
        self,
        title: str,
        *body,
        theme: AITheme | None = None,
        **kwargs,
    ) -> None:
        from manim import DOWN, Text, WHITE

        super().__init__(**kwargs)
        theme = theme or DEFAULT_THEME
        head = Text(title, font_size=theme.title_size, color=WHITE, weight="BOLD")
        parts = VGroup(head, *body).arrange(DOWN, buff=0.35, aligned_edge=LEFT)
        self.add(parts)


def stub_concept(
    title: str,
    equation: str,
    note: str = "Skeleton — extend this visualizer.",
    theme: AITheme | None = None,
) -> VGroup:
    """Minimal compiling diagram for P2 chapters."""
    from manim import DOWN, MathTex, Text, WHITE

    theme = theme or DEFAULT_THEME
    return ConceptCard(
        title,
        MathTex(equation, font_size=theme.math_size),
        Text(note, font_size=22, color=theme.soft),
        theme=theme,
    )

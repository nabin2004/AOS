"""Transformer block diagram (d2l Ch 11.7)."""

from __future__ import annotations

from manim import DOWN, Rectangle, Text, VGroup, WHITE

from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


def _layer(label: str) -> VGroup:
    box = Rectangle(width=4.5, height=0.65, color=DEFAULT_THEME.primary, fill_opacity=0.2)
    return VGroup(box, Text(label, font_size=20, color=WHITE))


@register_concept(
    id="transformer_block",
    domain="transformer",
    chapter="11.7",
    title="Transformer Encoder Block",
    tags=["transformer"],
)
def build_transformer_block() -> VGroup:
    stack = VGroup(
        _layer("Multi-Head Self-Attention"),
        _layer("Add & Norm"),
        _layer("Feed-Forward"),
        _layer("Add & Norm"),
    ).arrange(DOWN, buff=0.18)
    title = Text("Transformer encoder block", font_size=26, color=WHITE)
    return VGroup(title, stack).arrange(DOWN, buff=0.3)

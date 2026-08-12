"""Softmax / classification (d2l Ch 4)."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, MathTex, Rectangle, Text, VGroup, WHITE

from manim_ai.compute import nn as nn_ops
from manim_ai.compute import sympy_forms
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


@register_concept(
    id="softmax",
    domain="neural_network",
    chapter="4.1",
    title="Softmax",
    tags=["classification"],
)
def build_softmax(logits: Sequence[float] | None = None) -> VGroup:
    logits = list(logits or [2.0, 1.0, 0.1])
    probs = nn_ops.softmax(logits)
    title = Text("Softmax", font_size=28, color=WHITE)
    eq = MathTex(sympy_forms.softmax_latex(), font_size=30)
    bars = VGroup()
    for p in probs:
        bar = Rectangle(width=0.6, height=max(0.15, 2.2 * float(p)), color=DEFAULT_THEME.primary, fill_opacity=0.7)
        lab = Text(f"{p:.2f}", font_size=18, color=WHITE)
        g = VGroup(bar, lab).arrange(DOWN, buff=0.1)
        bars.add(g)
    bars.arrange(RIGHT, buff=0.4)
    return VGroup(title, eq, bars).arrange(DOWN, buff=0.35)

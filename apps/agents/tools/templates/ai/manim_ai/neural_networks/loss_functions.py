"""Loss function diagrams (d2l Ch 3–4)."""

from __future__ import annotations

from manim import DOWN, MathTex, Text, VGroup, WHITE

from manim_ai.compute import nn as nn_ops
from manim_ai.compute import sympy_forms
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


@register_concept(
    id="mse_loss",
    domain="neural_network",
    chapter="3.1.3",
    title="Squared Loss",
    tags=["loss"],
)
def build_mse_loss() -> VGroup:
    example = nn_ops.mse_loss([1.0, 2.0], [1.5, 1.5])
    title = Text("Mean squared error", font_size=28, color=WHITE)
    eq = MathTex(sympy_forms.mse_latex(), font_size=34)
    note = Text(f"Example MSE([1,2],[1.5,1.5]) = {example:.3g}", font_size=20, color=DEFAULT_THEME.soft)
    return VGroup(title, eq, note).arrange(DOWN, buff=0.35)


@register_concept(
    id="cross_entropy",
    domain="neural_network",
    chapter="4.1.2",
    title="Cross-Entropy Loss",
    tags=["loss"],
)
def build_cross_entropy() -> VGroup:
    example = nn_ops.cross_entropy([2.0, 1.0, 0.1], target_index=0)
    title = Text("Cross-entropy", font_size=28, color=WHITE)
    eq = MathTex(r"L=-\sum_k y_k\log \hat y_k", font_size=34)
    note = Text(f"Example CE(logits, class=0) = {example:.3g}", font_size=20, color=DEFAULT_THEME.soft)
    return VGroup(title, eq, note).arrange(DOWN, buff=0.35)

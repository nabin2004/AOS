"""Linear regression visualizers (d2l Ch 3)."""

from __future__ import annotations

from manim import DOWN, Axes, Dot, MathTex, Text, VGroup, WHITE

from manim_ai.compute import nn as nn_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


@register_concept(
    id="linear_regression",
    domain="neural_network",
    chapter="3.1",
    title="Linear Regression",
    tags=["regression"],
)
def build_linear_regression(n: int = 12, seed: int = 0) -> VGroup:
    xs, ys = nn_ops.synthetic_regression(n=n, seed=seed, w=1.5, b=0.5, noise=0.35)
    axes = Axes(x_range=[-3, 3, 1], y_range=[-4, 4, 1], x_length=6, y_length=3.5).scale(0.75)
    dots = VGroup(*[Dot(axes.c2p(float(x), float(y)), radius=0.05, color=WHITE) for x, y in zip(xs, ys)])
    line = axes.plot(lambda x: 1.5 * x + 0.5, color=DEFAULT_THEME.highlight)
    eq = MathTex(r"\hat y = w x + b", font_size=30)
    eq.next_to(axes, DOWN, buff=0.25)
    title = Text("Linear regression", font_size=28, color=WHITE)
    return VGroup(title, axes, dots, line, eq).arrange(DOWN, buff=0.15)

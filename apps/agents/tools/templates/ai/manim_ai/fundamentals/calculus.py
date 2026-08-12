"""Calculus visualizers (d2l Ch 2.4)."""

from __future__ import annotations

from manim import (
    DOWN,
    Axes,
    Dot,
    DashedLine,
    MathTex,
    Text,
    VGroup,
    WHITE,
)

from manim_ai.compute import calculus
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


@register_concept(
    id="derivative",
    domain="fundamental",
    chapter="2.4.1",
    title="Derivative",
    description="Function curve with tangent at a point.",
    tags=["calculus"],
)
def build_derivative(x0: float = 1.0) -> VGroup:
    y0, slope = calculus.derivative_at(lambda x: x**2, x0)
    axes = Axes(x_range=[-1, 3, 1], y_range=[-1, 5, 1], x_length=6, y_length=4).scale(0.7)
    curve = axes.plot(lambda x: x**2, color=DEFAULT_THEME.primary)
    point = Dot(axes.c2p(x0, y0), color=DEFAULT_THEME.highlight)
    x1, x2 = x0 - 0.8, x0 + 0.8
    tangent = DashedLine(
        axes.c2p(x1, y0 + slope * (x1 - x0)),
        axes.c2p(x2, y0 + slope * (x2 - x0)),
        color=DEFAULT_THEME.accent,
    )
    label = MathTex(rf"f(x)=x^2,\ f'({x0:g})={slope:g}", font_size=28)
    label.next_to(axes, DOWN, buff=0.3)
    return VGroup(axes, curve, tangent, point, label)


@register_concept(
    id="chain_rule",
    domain="fundamental",
    chapter="2.4.4",
    title="Chain Rule",
    description="Composition diagram f(g(x)).",
    tags=["calculus"],
)
def build_chain_rule() -> VGroup:
    title = Text("Chain rule", font_size=30, color=WHITE)
    eq = MathTex(r"\frac{dy}{dx} = \frac{dy}{du}\frac{du}{dx}", font_size=36)
    boxes = MathTex(r"x \;\rightarrow\; u=g(x) \;\rightarrow\; y=f(u)", font_size=30)
    return VGroup(title, boxes, eq).arrange(DOWN, buff=0.4)


@register_concept(
    id="gradient_descent_path",
    domain="fundamental",
    chapter="2.4.3",
    title="Gradient Descent Path",
    description="1D quadratic loss with descent steps.",
    tags=["calculus", "optimization"],
)
def build_gradient_descent_path(start: float = 2.5, steps: int = 6, lr: float = 0.25) -> VGroup:
    axes = Axes(x_range=[-1, 3, 1], y_range=[0, 7, 1], x_length=6, y_length=3.5).scale(0.7)
    curve = axes.plot(lambda x: (x - 0.5) ** 2, color=DEFAULT_THEME.primary)
    xs = calculus.gradient_descent_1d(start=start, steps=steps, lr=lr)
    dots = VGroup(*[Dot(axes.c2p(xi, (xi - 0.5) ** 2), color=DEFAULT_THEME.highlight) for xi in xs])
    label = Text("Gradient descent on (x−0.5)²", font_size=24, color=WHITE)
    label.next_to(axes, DOWN, buff=0.25)
    return VGroup(axes, curve, dots, label)

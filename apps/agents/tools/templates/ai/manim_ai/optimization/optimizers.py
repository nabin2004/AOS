"""Optimizer visualizers (d2l Ch 12)."""

from __future__ import annotations

from manim import DOWN, Axes, Dot, MathTex, Text, VGroup, WHITE

from manim_ai.compute import optim as optim_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


def _path_plot(xs: list[float], title: str) -> VGroup:
    axes = Axes(x_range=[-1, 3, 1], y_range=[0, 7, 1], x_length=6, y_length=3.5).scale(0.65)
    curve = axes.plot(lambda x: (x - 0.5) ** 2, color=DEFAULT_THEME.primary)
    dots = VGroup(*[Dot(axes.c2p(xi, (xi - 0.5) ** 2), color=DEFAULT_THEME.highlight) for xi in xs])
    lab = Text(title, font_size=20, color=WHITE)
    lab.next_to(axes, DOWN, buff=0.15)
    return VGroup(axes, curve, dots, lab)


@register_concept(
    id="sgd",
    domain="optimization",
    chapter="12.4",
    title="Stochastic Gradient Descent",
    tags=["optimizer"],
)
def build_sgd() -> VGroup:
    xs = optim_ops.sgd_path(start=2.5, steps=8, lr=0.25)
    path = _path_plot(xs, "SGD on (w−0.5)²")
    title = Text("SGD", font_size=26, color=WHITE)
    eq = MathTex(r"w \leftarrow w - \eta \nabla L_i(w)", font_size=28)
    return VGroup(title, path, eq).arrange(DOWN, buff=0.25)


@register_concept(
    id="momentum",
    domain="optimization",
    chapter="12.6",
    title="Momentum",
    tags=["optimizer"],
)
def build_momentum() -> VGroup:
    xs = optim_ops.momentum_path(start=2.5, steps=8, lr=0.15, momentum=0.9)
    path = _path_plot(xs, "Momentum on (w−0.5)²")
    title = Text("Momentum", font_size=28, color=WHITE)
    eq = MathTex(
        r"v_t=\beta v_{t-1}+\nabla L(w),\quad w\leftarrow w-\eta v_t",
        font_size=28,
    )
    return VGroup(title, path, eq).arrange(DOWN, buff=0.3)


@register_concept(
    id="adam",
    domain="optimization",
    chapter="12.10",
    title="Adam",
    tags=["optimizer"],
)
def build_adam() -> VGroup:
    xs = optim_ops.adam_path(start=2.5, steps=8, lr=0.3)
    path = _path_plot(xs, "Adam on (w−0.5)²")
    title = Text("Adam", font_size=28, color=WHITE)
    eq = MathTex(r"m_t, v_t\ \text{bias-corrected};\ w\leftarrow w-\eta\frac{m_t}{\sqrt{v_t}+\epsilon}", font_size=26)
    note = Text("Adaptive per-parameter learning rates", font_size=20, color=DEFAULT_THEME.soft)
    return VGroup(title, path, eq, note).arrange(DOWN, buff=0.25)


@register_concept(
    id="rmsprop",
    domain="optimization",
    chapter="12.9",
    title="RMSProp",
    tags=["optimizer"],
)
def build_rmsprop() -> VGroup:
    xs = optim_ops.rmsprop_path(start=2.5, steps=8, lr=0.2)
    path = _path_plot(xs, "RMSProp on (w−0.5)²")
    title = Text("RMSProp", font_size=28, color=WHITE)
    eq = MathTex(r"w \leftarrow w - \eta \frac{g}{\sqrt{s}+\epsilon}", font_size=28)
    return VGroup(title, path, eq).arrange(DOWN, buff=0.3)

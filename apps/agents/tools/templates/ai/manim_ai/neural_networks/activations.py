"""Activation function plots (d2l Ch 5.1.2)."""

from __future__ import annotations

from manim import DOWN, Axes, MathTex, Text, VGroup, WHITE

from manim_ai.compute import nn as nn_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


def _line_from_samples(axes: Axes, xs, ys, color):
    return axes.plot_line_graph(
        x_values=[float(x) for x in xs],
        y_values=[float(y) for y in ys],
        add_vertex_dots=False,
        line_color=color,
    )["line_graph"]


@register_concept(
    id="activations",
    domain="neural_network",
    chapter="5.1.2",
    title="Activation Functions",
    tags=["activation"],
)
def build_activations() -> VGroup:
    samples = nn_ops.activation_curves(kind="all")
    axes = Axes(x_range=[-3, 3, 1], y_range=[-1.5, 2, 1], x_length=5.5, y_length=3).scale(0.85)
    relu = _line_from_samples(axes, *samples["relu"], DEFAULT_THEME.primary)
    sigmoid = _line_from_samples(axes, *samples["sigmoid"], DEFAULT_THEME.secondary)
    tanh = _line_from_samples(axes, *samples["tanh"], DEFAULT_THEME.attention)
    legend = MathTex(r"\text{ReLU},\ \sigma,\ \tanh", font_size=26)
    legend.next_to(axes, DOWN, buff=0.25)
    title = Text("Activations (torch CPU)", font_size=28, color=WHITE)
    return VGroup(title, axes, relu, sigmoid, tanh, legend).arrange(DOWN, buff=0.2)


@register_concept(
    id="relu",
    domain="neural_network",
    chapter="5.1.2",
    title="ReLU",
    tags=["activation"],
)
def build_relu() -> VGroup:
    samples = nn_ops.activation_curves(kind="relu", x_min=-2, x_max=2)
    axes = Axes(x_range=[-2, 2, 1], y_range=[-0.5, 2, 1], x_length=5, y_length=3).scale(0.8)
    curve = _line_from_samples(axes, *samples["relu"], DEFAULT_THEME.highlight)
    label = MathTex(r"\mathrm{ReLU}(x)=\max(0,x)", font_size=28)
    label.next_to(axes, DOWN, buff=0.25)
    return VGroup(axes, curve, label)

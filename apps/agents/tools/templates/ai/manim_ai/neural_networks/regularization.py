"""Regularization visualizers (d2l Ch 3.7, 5.6)."""

from __future__ import annotations

from manim import DOWN, Circle, MathTex, Text, VGroup, WHITE

from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME
from manim_ai.neural_networks.mlp import Network


@register_concept(
    id="weight_decay",
    domain="neural_network",
    chapter="3.7",
    title="Weight Decay",
    tags=["regularization"],
)
def build_weight_decay() -> VGroup:
    title = Text("Weight decay (L2)", font_size=28, color=WHITE)
    eq = MathTex(r"L = L_0 + \frac{\lambda}{2}\|w\|_2^2", font_size=32)
    return VGroup(title, eq).arrange(DOWN, buff=0.4)


@register_concept(
    id="dropout",
    domain="neural_network",
    chapter="5.6",
    title="Dropout",
    tags=["regularization"],
)
def build_dropout(layers: list[int] | None = None, drop_frac: float = 0.4) -> VGroup:
    layers = layers or [4, 5, 4]
    net = Network(layers)
    # grey out some hidden neurons
    hidden = net.layer_groups[1]
    n_drop = max(1, int(len(hidden) * drop_frac))
    for i, node in enumerate(hidden):
        if i < n_drop:
            node.set_fill(DEFAULT_THEME.soft, opacity=0.15)
            node.set_stroke(DEFAULT_THEME.soft, opacity=0.35)
    title = Text("Dropout", font_size=28, color=WHITE)
    note = Text("Dropped units shown dimmed", font_size=20, color=DEFAULT_THEME.soft)
    return VGroup(title, net, note).arrange(DOWN, buff=0.3)

"""Backprop diagram (d2l Ch 5.3)."""

from __future__ import annotations

from collections.abc import Sequence

from manim_ai.core.registry import register_concept
from manim_ai.neural_networks.mlp import build_forward_backward


@register_concept(
    id="backpropagation",
    domain="neural_network",
    chapter="5.3",
    title="Backpropagation",
    tags=["backprop"],
)
def build_backpropagation(sizes: Sequence[int] | None = None, seed: int = 0):
    return build_forward_backward(sizes=sizes, seed=seed)

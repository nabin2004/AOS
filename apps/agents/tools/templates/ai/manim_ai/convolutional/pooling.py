"""Pooling visualizers (d2l Ch 7.5)."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, MathTex, Text, VGroup, WHITE

from manim_ai.compute import conv as conv_ops
from manim_ai.compute import tensors as tensor_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.utils import matrix_grid


@register_concept(
    id="pooling",
    domain="convolutional",
    chapter="7.5",
    title="Pooling",
    tags=["cnn", "pooling"],
)
def build_pooling(
    data: Sequence[Sequence[float]] | None = None,
    pool: str = "max",
) -> VGroup:
    data = data or [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]]
    if pool == "avg":
        out = conv_ops.avg_pool2d(data, kernel_size=2)
    else:
        out = conv_ops.max_pool2d(data, kernel_size=2)
    out_grid = tensor_ops.round_grid(out, decimals=1)
    left = VGroup(Text("Input", font_size=20, color=WHITE), matrix_grid(data, cell=0.45)).arrange(DOWN, buff=0.1)
    right = VGroup(
        Text(f"{pool}-pool 2×2", font_size=20, color=WHITE),
        matrix_grid(out_grid, cell=0.55),
    ).arrange(DOWN, buff=0.1)
    return VGroup(left, MathTex(r"\to", font_size=36), right).arrange(RIGHT, buff=0.4)

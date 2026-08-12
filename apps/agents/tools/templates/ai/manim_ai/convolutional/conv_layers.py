"""Convolution visualizers (d2l Ch 7)."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, MathTex, Text, VGroup, WHITE

from manim_ai.compute import conv as conv_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME
from manim_ai.core.utils import highlight_cell, matrix_grid


@register_concept(
    id="convolution",
    domain="convolutional",
    chapter="7.2",
    title="Cross-Correlation / Convolution",
    tags=["cnn"],
)
def build_convolution(
    image: Sequence[Sequence[float]] | None = None,
    kernel: Sequence[Sequence[float]] | None = None,
) -> VGroup:
    image = image or [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    kernel = kernel or [[0, 1], [2, 3]]
    img = matrix_grid(image, cell=0.5)
    ker = matrix_grid(kernel, cell=0.5)
    cols = len(image[0])
    for r in range(len(kernel)):
        for c in range(len(kernel[0])):
            highlight_cell(img, r * cols + c, color=DEFAULT_THEME.highlight, opacity=0.45)
    out_arr = conv_ops.cross_correlate(image, kernel)
    # First output cell matches the highlighted window
    out_val = float(out_arr.flat[0]) if out_arr.ndim else float(out_arr)
    out = matrix_grid([[round(out_val, 2)]], cell=0.6)
    left = VGroup(Text("Input", font_size=20, color=WHITE), img).arrange(DOWN, buff=0.15)
    mid = VGroup(Text("Kernel", font_size=20, color=WHITE), ker).arrange(DOWN, buff=0.15)
    right = VGroup(Text("Output cell", font_size=20, color=WHITE), out).arrange(DOWN, buff=0.15)
    return VGroup(left, MathTex(r"*", font_size=36), mid, MathTex(r"\to", font_size=36), right).arrange(
        RIGHT, buff=0.3
    )


@register_concept(
    id="padding_stride",
    domain="convolutional",
    chapter="7.3",
    title="Padding and Stride",
    tags=["cnn"],
)
def build_padding_stride(padding: int = 1, stride: int = 2) -> VGroup:
    title = Text("Padding & stride", font_size=28, color=WHITE)
    eq = MathTex(
        rf"\text{{pad}}={padding},\ \text{{stride}}={stride}",
        font_size=30,
    )
    note = Text("Output size shrinks with larger stride; padding preserves edges", font_size=20, color=DEFAULT_THEME.soft)
    return VGroup(title, eq, note).arrange(DOWN, buff=0.35)

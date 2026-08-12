"""Linear algebra visualizers (d2l Ch 2.3)."""

from __future__ import annotations

from collections.abc import Sequence

from manim import (
    DOWN,
    RIGHT,
    Arrow,
    Dot,
    MathTex,
    NumberPlane,
    Text,
    VGroup,
    WHITE,
)

from manim_ai.compute import linalg
from manim_ai.compute import tensors as tensor_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME
from manim_ai.core.utils import matrix_grid


@register_concept(
    id="vector_2d",
    domain="fundamental",
    chapter="2.3.2",
    title="Vector",
    description="2D vector arrow with coordinates.",
    tags=["linalg", "vector"],
)
def build_vector_2d(values: Sequence[float] | None = None) -> VGroup:
    values = list(values or [2.0, 1.5])
    plane = NumberPlane(
        x_range=[-1, 4, 1],
        y_range=[-1, 3, 1],
        background_line_style={"stroke_opacity": 0.35},
    ).scale(0.55)
    start = plane.c2p(0, 0)
    arrow = Arrow(start, plane.c2p(values[0], values[1]), buff=0, color=DEFAULT_THEME.highlight)
    tip = Dot(plane.c2p(values[0], values[1]), color=DEFAULT_THEME.accent)
    label = MathTex(
        rf"\mathbf{{v}}=[{values[0]:g},\,{values[1]:g}]",
        font_size=28,
    )
    label.next_to(plane, DOWN, buff=0.25)
    return VGroup(plane, arrow, tip, label)


@register_concept(
    id="matrix_multiply",
    domain="fundamental",
    chapter="2.3.10",
    title="Matrix–Matrix Multiplication",
    description="Show A, B and product C = AB.",
    tags=["linalg", "matmul"],
)
def build_matrix_multiply(
    A: Sequence[Sequence[float]] | None = None,
    B: Sequence[Sequence[float]] | None = None,
) -> VGroup:
    A = A or [[1, 2], [3, 4]]
    B = B or [[5, 6], [7, 8]]
    C = tensor_ops.round_grid(linalg.torch_matmul(A, B), decimals=4)
    ga = matrix_grid(A)
    gb = matrix_grid(B)
    gc = matrix_grid(C)
    la = Text("A", font_size=22, color=WHITE)
    lb = Text("B", font_size=22, color=WHITE)
    lc = Text("C = AB", font_size=22, color=DEFAULT_THEME.positive)
    left = VGroup(la, ga).arrange(DOWN, buff=0.15)
    mid = VGroup(lb, gb).arrange(DOWN, buff=0.15)
    right = VGroup(lc, gc).arrange(DOWN, buff=0.15)
    return VGroup(left, MathTex(r"\times", font_size=36), mid, MathTex(r"=", font_size=36), right).arrange(
        RIGHT, buff=0.3
    )


@register_concept(
    id="vector_norms",
    domain="fundamental",
    chapter="2.3.11",
    title="Norms",
    description="Compare L1 and L2 norms of a vector.",
    tags=["linalg", "norm"],
)
def build_vector_norms(values: Sequence[float] | None = None) -> VGroup:
    values = list(values or [3.0, -4.0])
    norms = linalg.vector_norms(values)
    title = Text("Norms", font_size=30, color=WHITE)
    eq = MathTex(
        rf"\|v\|_1 = {norms['l1']:g},\quad \|v\|_2 = {norms['l2']:g}",
        font_size=32,
    )
    vec = MathTex(rf"v = [{values[0]:g},\,{values[1]:g}]", font_size=28)
    return VGroup(title, vec, eq).arrange(DOWN, buff=0.35)


@register_concept(
    id="svd",
    domain="fundamental",
    chapter="2.3",
    title="SVD",
    description="Singular values via torch.linalg.svd on CPU.",
    tags=["linalg", "svd"],
)
def build_svd(A: Sequence[Sequence[float]] | None = None) -> VGroup:
    A = A or [[3.0, 1.0], [1.0, 3.0]]
    _u, s, _vh = linalg.torch_svd(A)
    title = Text("SVD (torch.linalg, CPU)", font_size=26, color=WHITE)
    grid = matrix_grid(A)
    s_tex = MathTex(
        r"\sigma = [" + ",".join(f"{float(v):.3g}" for v in s) + r"]",
        font_size=28,
    )
    return VGroup(title, grid, s_tex).arrange(DOWN, buff=0.3)

"""Tensor / data-structure visualizers (d2l Ch 2.1)."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, Text, VGroup, WHITE

from manim_ai.compute import tensors as tensor_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME
from manim_ai.core.utils import highlight_cell, matrix_grid, vector_row


@register_concept(
    id="tensor_grid",
    domain="fundamental",
    chapter="2.1",
    title="Tensor / Matrix Grid",
    description="Display a 2D tensor as a labeled grid.",
    tags=["tensor", "data"],
)
def build_tensor_grid(
    data: Sequence[Sequence[float | int]] | None = None,
    title: str = "Tensor",
) -> VGroup:
    data = data or [[1, 2, 3], [4, 5, 6]]
    shape = tensor_ops.shape_of(data)
    grid = matrix_grid(data)
    label = Text(title, font_size=28, color=WHITE)
    shape_lab = Text(f"shape = {shape[0]}×{shape[1]}", font_size=22, color=DEFAULT_THEME.soft)
    head = VGroup(label, shape_lab).arrange(DOWN, buff=0.15)
    return VGroup(head, grid).arrange(DOWN, buff=0.35)


@register_concept(
    id="tensor_indexing",
    domain="fundamental",
    chapter="2.1.2",
    title="Indexing and Slicing",
    description="Highlight selected tensor indices.",
    tags=["tensor", "indexing"],
)
def build_tensor_indexing(
    data: Sequence[Sequence[float | int]] | None = None,
    indices: Sequence[tuple[int, int]] | None = None,
) -> VGroup:
    data = data or [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    indices = list(indices or [(0, 1), (2, 2)])
    _ = tensor_ops.index_select(data, indices)
    grid = matrix_grid(data)
    cols = len(data[0])
    for r, c in indices:
        highlight_cell(grid, r * cols + c)
    caption = Text(f"indices = {list(indices)}", font_size=22, color=DEFAULT_THEME.highlight)
    return VGroup(grid, caption).arrange(DOWN, buff=0.3)


@register_concept(
    id="broadcasting",
    domain="fundamental",
    chapter="2.1.4",
    title="Broadcasting",
    description="Show how a vector broadcasts onto a matrix.",
    tags=["tensor", "broadcasting"],
)
def build_broadcasting(
    matrix: Sequence[Sequence[float]] | None = None,
    vector: Sequence[float] | None = None,
) -> VGroup:
    matrix = matrix or [[1, 2, 3], [4, 5, 6]]
    vector = vector or [10, 20, 30]
    a = matrix_grid(matrix)
    b = vector_row(vector)
    a_label = Text("A", font_size=24, color=WHITE)
    b_label = Text("b (broadcast)", font_size=24, color=WHITE)
    left = VGroup(a_label, a).arrange(DOWN, buff=0.2)
    right = VGroup(b_label, b).arrange(DOWN, buff=0.2)
    result_data = tensor_ops.round_grid(tensor_ops.broadcast_add(matrix, vector), decimals=4)
    out = matrix_grid(result_data)
    out_label = Text("A + b", font_size=24, color=DEFAULT_THEME.positive)
    result = VGroup(out_label, out).arrange(DOWN, buff=0.2)
    plus = Text("+", font_size=36, color=WHITE)
    eq = Text("→", font_size=36, color=WHITE)
    return VGroup(left, plus, right, eq, result).arrange(RIGHT, buff=0.35)

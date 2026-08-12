"""Linear algebra concept builders."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, Arrow, Dot, MathTex, Text, VGroup, WHITE

from manim_math.compute import eig_2x2, matmul
from manim_math.registry import register_concept
from manim_viz import DEFAULT_THEME, labeled_vector_on_plane, make_plane, matrix_grid


@register_concept(
    id="vector_2d",
    domain="math",
    chapter="1.1",
    title="2D Vector",
    tags=["linalg", "vector"],
)
def build_vector_2d(values: Sequence[float] | None = None) -> VGroup:
    values = list(values or [2.0, 1.2])
    plane = make_plane(x_range=(-1, 4, 1), y_range=(-1, 3, 1))
    arrow = labeled_vector_on_plane(plane, values, label=rf"\vec v")
    lab = MathTex(rf"\mathbf{{v}}=[{values[0]:g},\,{values[1]:g}]", font_size=28)
    lab.next_to(plane, DOWN, buff=0.25)
    return VGroup(plane, arrow, lab)


@register_concept(
    id="matrix_multiply",
    domain="math",
    chapter="1.2",
    title="Matrix Multiplication",
    tags=["linalg"],
)
def build_matrix_multiply(
    A: Sequence[Sequence[float]] | None = None,
    B: Sequence[Sequence[float]] | None = None,
) -> VGroup:
    A = A or [[1, 2], [3, 4]]
    B = B or [[0, 1], [1, 0]]
    C = np_round(matmul(A, B))
    left = VGroup(Text("A", font_size=20, color=WHITE), matrix_grid(A)).arrange(DOWN, buff=0.1)
    mid = VGroup(Text("B", font_size=20, color=WHITE), matrix_grid(B)).arrange(DOWN, buff=0.1)
    right = VGroup(Text("AB", font_size=20, color=DEFAULT_THEME.positive), matrix_grid(C)).arrange(DOWN, buff=0.1)
    return VGroup(left, MathTex(r"\times", font_size=32), mid, MathTex(r"=", font_size=32), right).arrange(
        RIGHT, buff=0.3
    )


def np_round(arr, decimals: int = 2):
    import numpy as np

    return np.round(arr, decimals).tolist()


@register_concept(
    id="eigen_2x2",
    domain="math",
    chapter="1.3",
    title="Eigenvalues (2×2)",
    tags=["linalg", "eigen"],
)
def build_eigen_2x2(A: Sequence[Sequence[float]] | None = None) -> VGroup:
    A = A or [[2.0, 1.0], [1.0, 2.0]]
    w, v = eig_2x2(A)
    title = Text("Eigenvalues / eigenvectors", font_size=26, color=WHITE)
    grid = matrix_grid(A)
    vals = MathTex(
        rf"\lambda_1={float(w[0]):.3g},\ \lambda_2={float(w[1]):.3g}",
        font_size=28,
    )
    plane = make_plane(x_range=(-3, 3, 1), y_range=(-3, 3, 1), scale=0.55)
    e1 = labeled_vector_on_plane(plane, v[:, 0], color=DEFAULT_THEME.highlight, label=r"v_1")
    e2 = labeled_vector_on_plane(plane, v[:, 1], color=DEFAULT_THEME.secondary, label=r"v_2")
    return VGroup(title, grid, vals, VGroup(plane, e1, e2)).arrange(DOWN, buff=0.25)

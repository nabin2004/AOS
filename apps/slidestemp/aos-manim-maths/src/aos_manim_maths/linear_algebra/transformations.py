from __future__ import annotations

from typing import Optional, Dict, Any, List
import numpy as np
from manim import (
    NumberPlane,
    Arrow,
    Polygon,
    MathTex,
    VGroup,
    ORIGIN,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig


class MatrixTransformationVisualizer:
    """Visualizes 2D linear transformations, basis vector mappings, and determinant areas."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_transformation_mobjects(
        self,
        matrix: list[list[float]] | np.ndarray,
        plane_width: float = 8.0,
        plane_height: float = 6.0,
    ) -> Dict[str, Any]:
        mat = np.array(matrix, dtype=float)
        det = float(np.linalg.det(mat))
        t = self.theme

        plane = NumberPlane(
            x_range=(-4, 4, 1),
            y_range=(-3, 3, 1),
            x_length=plane_width,
            y_length=plane_height,
            background_line_style={"stroke_color": t.border, "stroke_width": 1.0, "stroke_opacity": 0.4},
            axis_config={"color": t.text_muted, "stroke_width": 2},
        )

        # Standard basis vectors
        i_hat = np.array([1.0, 0.0, 0.0])
        j_hat = np.array([0.0, 1.0, 0.0])

        # Transformed basis vectors
        i_trans = np.array([mat[0, 0], mat[1, 0], 0.0])
        j_trans = np.array([mat[0, 1], mat[1, 1], 0.0])

        # Origin point on plane
        p_origin = plane.c2p(0, 0)
        p_i = plane.c2p(i_trans[0], i_trans[1])
        p_j = plane.c2p(j_trans[0], j_trans[1])
        p_corner = plane.c2p(i_trans[0] + j_trans[0], i_trans[1] + j_trans[1])

        arrow_i = Arrow(p_origin, p_i, buff=0, color=t.accent, stroke_width=4.0)
        arrow_j = Arrow(p_origin, p_j, buff=0, color=t.primary, stroke_width=4.0)

        # Determinant area parallelogram
        det_poly = Polygon(
            p_origin,
            p_i,
            p_corner,
            p_j,
            fill_color=t.highlight_a,
            fill_opacity=0.3,
            stroke_color=t.highlight_a,
            stroke_width=2.0,
        )

        tex_mat = MathTex(
            rf"A = \begin{{pmatrix}} {mat[0,0]:.1f} & {mat[0,1]:.1f} \\ {mat[1,0]:.1f} & {mat[1,1]:.1f} \end{{pmatrix}}, \quad \det(A) = {det:.2f}",
            color=t.text_main,
            font_size=24,
        ).next_to(plane, UP, aligned_edge=LEFT, buff=0.2)

        return {
            "plane": plane,
            "arrow_i": arrow_i,
            "arrow_j": arrow_j,
            "det_polygon": det_poly,
            "label": tex_mat,
            "matrix": mat,
            "determinant": det,
            "i_transformed": i_trans,
            "j_transformed": j_trans,
        }

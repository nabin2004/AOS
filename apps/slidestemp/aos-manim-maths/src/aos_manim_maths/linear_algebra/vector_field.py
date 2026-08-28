from __future__ import annotations

from typing import Optional, Callable, Dict, Any
import numpy as np
from manim import (
    VectorField,
    ArrowVectorField,
    Axes,
    MathTex,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig


class VectorFieldVisualizer:
    """Generates 2D vector field arrows with theme-aware color mapping."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_vector_field_mobjects(
        self,
        func: Callable[[np.ndarray], np.ndarray],
        x_range: tuple[float, float, float] = (-4, 4, 1),
        y_range: tuple[float, float, float] = (-3, 3, 1),
        field_length: float = 0.6,
        latex_title: str = r"\vec{F}(x, y)",
    ) -> Dict[str, Any]:
        t = self.theme

        vf = ArrowVectorField(
            func,
            x_range=x_range,
            y_range=y_range,
            length_func=lambda norm: field_length * (1 - np.exp(-norm / 2)),
            colors=[t.primary, t.secondary, t.accent],
        )

        tex_title = MathTex(latex_title, color=t.text_main, font_size=26)
        tex_title.to_corner(UP + LEFT)

        return {
            "vector_field": vf,
            "label": tex_title,
        }

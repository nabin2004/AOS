from __future__ import annotations

from typing import Optional, Union, Callable, Dict, Any
import numpy as np
import sympy as sp
from manim import (
    Axes,
    Dot,
    Line,
    MathTex,
    VGroup,
    Create,
    Transform,
    FadeIn,
    Write,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig, ValidationResult, BaseValidator, ValidationSeverity


def compute_derivative_data(
    expression_str: str,
    x_val: float,
    x_range: tuple[float, float] = (-3, 3),
) -> Dict[str, Any]:
    """Symbolically differentiates expression and computes numerical values."""
    x = sp.Symbol('x')
    expr = sp.sympify(expression_str)
    diff_expr = sp.diff(expr, x)

    f_func = sp.lambdify(x, expr, modules=["numpy"])
    df_func = sp.lambdify(x, diff_expr, modules=["numpy"])

    y_val = float(expr.subs(x, x_val))
    slope = float(diff_expr.subs(x, x_val))

    return {
        "symbolic_expr": str(expr),
        "symbolic_diff": str(diff_expr),
        "latex_expr": sp.latex(expr),
        "latex_diff": sp.latex(diff_expr),
        "f": f_func,
        "df": df_func,
        "x_val": x_val,
        "y_val": y_val,
        "slope": slope,
    }


class DerivativeVisualizer:
    """Creates mathematically precise derivative and tangent visualization mobjects."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_derivative_mobjects(
        self,
        expression_str: str,
        x_val: float,
        x_range: tuple[float, float, float] = (-3, 3, 1),
        y_range: tuple[float, float, float] = (-2, 8, 2),
        axes_width: float = 7.0,
        axes_height: float = 4.5,
    ) -> Dict[str, Any]:
        data = compute_derivative_data(expression_str, x_val)
        t = self.theme

        axes = Axes(
            x_range=x_range,
            y_range=y_range,
            x_length=axes_width,
            y_length=axes_height,
            axis_config={"color": t.text_muted, "stroke_width": 2},
        )
        curve = axes.plot(data["f"], color=t.primary, stroke_width=3.5)

        pt_coord = axes.c2p(data["x_val"], data["y_val"])
        point = Dot(pt_coord, color=t.accent, radius=0.09)

        # Tangent line segment
        dx = 1.5
        x_left = data["x_val"] - dx
        y_left = data["y_val"] - data["slope"] * dx
        x_right = data["x_val"] + dx
        y_right = data["y_val"] + data["slope"] * dx

        p_start = axes.c2p(x_left, y_left)
        p_end = axes.c2p(x_right, y_right)
        tangent_line = Line(p_start, p_end, color=t.accent_secondary, stroke_width=3.0)

        # Labels
        tex_f = MathTex(f"f(x) = {data['latex_expr']}", color=t.primary, font_size=24)
        tex_df = MathTex(
            f"f'({data['x_val']}) = {data['slope']:.2f}",
            color=t.accent_secondary,
            font_size=24,
        )
        label_group = VGroup(tex_f, tex_df).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        label_group.next_to(axes, UP, aligned_edge=LEFT, buff=0.2)

        return {
            "axes": axes,
            "curve": curve,
            "point": point,
            "tangent_line": tangent_line,
            "labels": label_group,
            "data": data,
        }

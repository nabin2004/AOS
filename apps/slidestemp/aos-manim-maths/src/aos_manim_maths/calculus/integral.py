from __future__ import annotations

from typing import Optional, Dict, Any
import numpy as np
import sympy as sp
import scipy.integrate as integrate
from manim import (
    Axes,
    MathTex,
    VGroup,
    Rectangle,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig


def compute_integral_data(
    expression_str: str,
    a: float,
    b: float,
) -> Dict[str, Any]:
    """Computes symbolic and numerical definite integrals."""
    x = sp.Symbol('x')
    expr = sp.sympify(expression_str)
    anti_deriv = sp.integrate(expr, x)
    sym_val = sp.integrate(expr, (x, a, b))

    f_func = sp.lambdify(x, expr, modules=["numpy"])
    num_val, num_err = integrate.quad(lambda val: float(f_func(val)), a, b)

    return {
        "symbolic_expr": str(expr),
        "latex_expr": sp.latex(expr),
        "latex_antideriv": sp.latex(anti_deriv),
        "symbolic_result": float(sym_val),
        "numerical_result": num_val,
        "numerical_error": num_err,
        "f": f_func,
        "a": a,
        "b": b,
    }


class IntegralVisualizer:
    """Creates Riemann sums and area-under-curve visualization mobjects."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_integral_mobjects(
        self,
        expression_str: str,
        a: float,
        b: float,
        num_rectangles: int = 16,
        x_range: tuple[float, float, float] = (-1, 5, 1),
        y_range: tuple[float, float, float] = (-1, 8, 2),
        axes_width: float = 7.0,
        axes_height: float = 4.5,
    ) -> Dict[str, Any]:
        data = compute_integral_data(expression_str, a, b)
        t = self.theme

        axes = Axes(
            x_range=x_range,
            y_range=y_range,
            x_length=axes_width,
            y_length=axes_height,
            axis_config={"color": t.text_muted, "stroke_width": 2},
        )
        curve = axes.plot(data["f"], color=t.primary, stroke_width=3.5)

        # Shaded area
        area = axes.get_area(
            curve,
            x_range=(a, b),
            color=t.accent_secondary,
            opacity=0.35,
        )

        # Riemann rectangles
        riemann_rects = axes.get_riemann_rectangles(
            curve,
            x_range=(a, b),
            dx=(b - a) / num_rectangles,
            color=(t.accent, t.primary),
            stroke_width=1.0,
            fill_opacity=0.5,
        )

        tex_int = MathTex(
            rf"\int_{{{a}}}^{{{b}}} {data['latex_expr']} \, dx = {data['symbolic_result']:.4f}",
            color=t.text_main,
            font_size=26,
        )
        tex_int.next_to(axes, UP, aligned_edge=LEFT, buff=0.2)

        return {
            "axes": axes,
            "curve": curve,
            "area": area,
            "riemann_rectangles": riemann_rects,
            "label": tex_int,
            "data": data,
        }

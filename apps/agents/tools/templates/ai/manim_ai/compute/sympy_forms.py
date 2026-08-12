"""Sympy helpers for lecture equations."""

from __future__ import annotations

import sympy as sp


def latex(expr: str) -> str:
    """Sympify an expression string and return LaTeX."""
    return sp.latex(sp.sympify(expr))


def mse_latex() -> str:
    return r"L=\frac{1}{2n}\sum_{i=1}^{n}(y_i-\hat y_i)^2"


def softmax_latex() -> str:
    return r"\hat y = \mathrm{softmax}(o)"

"""Math compute backends (numpy / scipy / sympy)."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy import linalg as sla
from scipy.integrate import solve_ivp


def matmul(A, B) -> np.ndarray:
    return np.asarray(A, dtype=float) @ np.asarray(B, dtype=float)


def eig_2x2(A) -> tuple[np.ndarray, np.ndarray]:
    w, v = np.linalg.eig(np.asarray(A, dtype=float))
    return np.real(w), np.real(v)


def svd(A) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    u, s, vh = sla.svd(np.asarray(A, dtype=float), full_matrices=False)
    return u, s, vh


def sample_function(
    func: Callable[[float], float],
    x_min: float = -3.0,
    x_max: float = 3.0,
    n: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    xs = np.linspace(x_min, x_max, n)
    ys = np.array([float(func(float(x))) for x in xs])
    return xs, ys


def derivative_at(func: Callable[[float], float], x0: float, h: float = 1e-5) -> tuple[float, float]:
    y0 = float(func(x0))
    dy = (float(func(x0 + h)) - float(func(x0 - h))) / (2 * h)
    return y0, dy


def riemann_sum(
    func: Callable[[float], float],
    a: float = 0.0,
    b: float = 2.0,
    n: int = 6,
    method: str = "mid",
) -> dict:
    xs = np.linspace(a, b, n + 1)
    dx = (b - a) / n
    if method == "left":
        sample = xs[:-1]
    elif method == "right":
        sample = xs[1:]
    else:
        sample = (xs[:-1] + xs[1:]) / 2
    heights = np.array([float(func(float(x))) for x in sample])
    area = float(np.sum(heights) * dx)
    return {"edges": xs, "sample_x": sample, "heights": heights, "dx": dx, "area": area}


def harmonic_oscillator(
    omega: float = 1.5,
    x0: float = 1.0,
    v0: float = 0.0,
    t_end: float = 8.0,
    n: int = 200,
) -> dict:
    """x'' = -ω² x  →  state [x, v]."""

    def f(_t, state):
        x, v = state
        return [v, -(omega**2) * x]

    sol = solve_ivp(f, (0.0, t_end), [x0, v0], t_eval=np.linspace(0, t_end, n), rtol=1e-6)
    return {"t": sol.t, "x": sol.y[0], "v": sol.y[1], "success": bool(sol.success)}


def latex_expr(expr: str) -> str:
    import sympy as sp

    return sp.latex(sp.sympify(expr))

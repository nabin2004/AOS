"""Calculus helpers via torch autograd on CPU + numpy trajectories."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import torch

from manim_ai.compute import device as cpu


def derivative_at(func: Callable[[torch.Tensor], torch.Tensor], x0: float) -> tuple[float, float]:
    """Return (f(x0), f'(x0)) using torch autograd on CPU."""
    x = cpu.tensor(float(x0), requires_grad=True, dtype=torch.float32)
    y = func(x)
    y.backward()
    return float(y.detach()), float(x.grad)


def finite_diff(func: Callable[[float], float], x0: float, h: float = 1e-5) -> float:
    return (func(x0 + h) - func(x0 - h)) / (2 * h)


def gradient_descent_1d(
    *,
    start: float = 2.5,
    steps: int = 6,
    lr: float = 0.25,
    target: float = 0.5,
) -> list[float]:
    """
    Minimize f(w)=(w-target)^2 with plain GD using torch on CPU.
    Returns iterate list including the start point.
    """
    w = cpu.tensor(float(start), requires_grad=True, dtype=torch.float32)
    xs = [float(w.detach())]
    for _ in range(steps):
        loss = (w - target) ** 2
        loss.backward()
        with torch.no_grad():
            w -= lr * w.grad
            w.grad = None
        xs.append(float(w.detach()))
    return xs


def sample_parabola(x_min: float = -1.0, x_max: float = 3.0, n: int = 100) -> tuple[np.ndarray, np.ndarray]:
    xs = np.linspace(x_min, x_max, n)
    ys = xs**2
    return xs, ys

"""Learning-rate schedule arrays (numpy)."""

from __future__ import annotations

import numpy as np


def constant(t: np.ndarray, base: float = 0.01) -> np.ndarray:
    return np.full_like(t, base, dtype=float)


def step_decay(t: np.ndarray, base: float = 0.01, drop: float = 0.1, every: int = 40) -> np.ndarray:
    return base * (drop ** np.floor(t / every))


def cosine(t: np.ndarray, base: float = 0.01, t_max: float = 100.0) -> np.ndarray:
    return base * (1 + np.cos(np.pi * t / t_max)) / 2


def schedule_curves(n: int = 100) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    t = np.linspace(0, 100, n)
    return {
        "constant": (t, constant(t)),
        "step": (t, step_decay(t)),
        "cosine": (t, cosine(t)),
    }

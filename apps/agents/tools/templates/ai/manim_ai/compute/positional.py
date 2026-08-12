"""Positional encoding (d2l formula) via numpy."""

from __future__ import annotations

import numpy as np


def sinusoidal_pe(length: int = 32, dim: int = 16) -> np.ndarray:
    """Return PE matrix of shape (length, dim)."""
    position = np.arange(length)[:, None]
    div = np.exp(np.arange(0, dim, 2) * -(np.log(10000.0) / dim))
    pe = np.zeros((length, dim))
    pe[:, 0::2] = np.sin(position * div)
    pe[:, 1::2] = np.cos(position * div)
    return pe


def pe_wave(kind: str = "sin", length: int = 64) -> tuple[np.ndarray, np.ndarray]:
    xs = np.linspace(0, length - 1, length)
    if kind == "cos":
        return xs, np.cos(xs / 3.0)
    return xs, np.sin(xs / 3.0)

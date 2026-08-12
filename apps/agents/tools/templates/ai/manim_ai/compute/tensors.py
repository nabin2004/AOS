"""Numpy tensor helpers — source of truth for array ops / broadcasting."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def as_array(data, dtype=float) -> np.ndarray:
    return np.asarray(data, dtype=dtype)


def broadcast_add(a, b) -> np.ndarray:
    """Elementwise add with numpy broadcasting."""
    return as_array(a) + as_array(b)


def index_select(data, indices: Sequence[tuple[int, ...]]) -> list:
    """Gather values at multi-index positions."""
    arr = as_array(data)
    return [arr[idx] for idx in indices]


def shape_of(data) -> tuple[int, ...]:
    return tuple(as_array(data).shape)


def round_grid(data, decimals: int = 2) -> list:
    arr = np.round(as_array(data), decimals=decimals)
    return arr.tolist()

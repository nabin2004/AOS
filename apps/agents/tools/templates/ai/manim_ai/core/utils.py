"""Shared Manim construction utilities."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    Square,
    Text,
    UP,
    VGroup,
    WHITE,
)

from manim_ai.core.theme import AITheme, DEFAULT_THEME


def matrix_grid(
    values: Sequence[Sequence[float | int | str]],
    *,
    cell: float = 0.55,
    theme: AITheme | None = None,
    precision: int = 2,
) -> VGroup:
    """Draw a 2D numeric/string grid as a matrix of squares."""
    theme = theme or DEFAULT_THEME
    rows = len(values)
    cols = len(values[0]) if rows else 0
    cells = VGroup()
    for r in range(rows):
        for c in range(cols):
            sq = Square(side_length=cell * 0.95)
            sq.set_fill(theme.primary, opacity=0.15)
            sq.set_stroke(WHITE, width=1)
            val = values[r][c]
            if isinstance(val, float):
                label = Text(f"{val:.{precision}f}", font_size=18, color=WHITE)
            else:
                label = Text(str(val), font_size=18, color=WHITE)
            group = VGroup(sq, label)
            group.move_to(
                RIGHT * (c - (cols - 1) / 2) * cell
                + DOWN * (r - (rows - 1) / 2) * cell
            )
            cells.add(group)
    return cells


def vector_row(
    values: Sequence[float | int | str],
    *,
    cell: float = 0.55,
    theme: AITheme | None = None,
) -> VGroup:
    return matrix_grid([list(values)], cell=cell, theme=theme)


def highlight_cell(grid: VGroup, index: int, color=None, opacity: float = 0.55) -> None:
    color = color or DEFAULT_THEME.highlight
    mob = grid[index]
    mob[0].set_fill(color, opacity=opacity)


def as_np(data) -> np.ndarray:
    return np.asarray(data, dtype=float)

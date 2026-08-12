"""Matrix / grid drawing utilities."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, Square, Text, VGroup, WHITE

from manim_viz.theme import DEFAULT_THEME, VizTheme


def matrix_grid(
    values: Sequence[Sequence[float | int | str]],
    *,
    cell: float = 0.55,
    theme: VizTheme | None = None,
    precision: int = 2,
) -> VGroup:
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

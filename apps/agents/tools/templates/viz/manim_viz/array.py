"""Array / bar-list primitives for DSA."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, Square, Text, VGroup, WHITE

from manim_viz.theme import DEFAULT_THEME, VizTheme


def array_cells(
    values: Sequence[float | int | str],
    *,
    cell: float = 0.7,
    theme: VizTheme | None = None,
) -> VGroup:
    theme = theme or DEFAULT_THEME
    cells = VGroup()
    for i, val in enumerate(values):
        sq = Square(side_length=cell * 0.9)
        sq.set_fill(theme.primary, opacity=0.2)
        sq.set_stroke(WHITE, width=1.5)
        label = Text(str(val), font_size=22, color=WHITE)
        idx = Text(str(i), font_size=14, color=theme.soft)
        body = VGroup(sq, label)
        g = VGroup(body, idx).arrange(DOWN, buff=0.08)
        cells.add(g)
    cells.arrange(RIGHT, buff=0.12)
    return cells


def array_bars(
    values: Sequence[float | int],
    *,
    theme: VizTheme | None = None,
    max_height: float = 2.8,
) -> VGroup:
    theme = theme or DEFAULT_THEME
    vals = [float(v) for v in values]
    peak = max(vals) if vals else 1.0
    bars = VGroup()
    for i, v in enumerate(vals):
        h = max(0.2, max_height * (v / peak if peak else 0))
        from manim import Rectangle

        rect = Rectangle(width=0.55, height=h, color=theme.primary, fill_opacity=0.75)
        lab = Text(str(int(v) if float(v).is_integer() else f"{v:g}"), font_size=16, color=WHITE)
        g = VGroup(rect, lab).arrange(DOWN, buff=0.06)
        bars.add(g)
    bars.arrange(RIGHT, buff=0.2)
    return bars


def highlight_indices(group: VGroup, indices: Sequence[int], color=None, opacity: float = 0.55) -> None:
    theme_color = color or DEFAULT_THEME.highlight
    for i in indices:
        if 0 <= i < len(group):
            mob = group[i]
            # cell or bar: first submob is usually the filled shape container
            target = mob[0][0] if hasattr(mob[0], "__getitem__") else mob[0]
            try:
                target.set_fill(theme_color, opacity=opacity)
            except Exception:
                mob.set_color(theme_color)

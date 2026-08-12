"""Plot helpers from sampled arrays."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, Rectangle, Text, VGroup, WHITE

from manim_viz.coords import make_axes
from manim_viz.theme import DEFAULT_THEME, VizTheme


def curve_from_samples(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    x_range=None,
    y_range=None,
    color=None,
    theme: VizTheme | None = None,
) -> VGroup:
    theme = theme or DEFAULT_THEME
    color = color or theme.primary
    xs = list(map(float, xs))
    ys = list(map(float, ys))
    if x_range is None:
        x_range = (min(xs) - 0.5, max(xs) + 0.5, 1)
    if y_range is None:
        pad = max(0.5, 0.1 * (max(ys) - min(ys) + 1e-9))
        y_range = (min(ys) - pad, max(ys) + pad, 1)
    axes = make_axes(x_range=x_range, y_range=y_range)
    line = axes.plot_line_graph(
        x_values=xs,
        y_values=ys,
        add_vertex_dots=False,
        line_color=color,
    )["line_graph"]
    return VGroup(axes, line)


def bar_chart(
    values: Sequence[float],
    *,
    labels: Sequence[str] | None = None,
    theme: VizTheme | None = None,
    max_height: float = 2.5,
) -> VGroup:
    theme = theme or DEFAULT_THEME
    vals = [float(v) for v in values]
    peak = max(abs(v) for v in vals) or 1.0
    bars = VGroup()
    for i, v in enumerate(vals):
        h = max(0.12, max_height * abs(v) / peak)
        rect = Rectangle(width=0.55, height=h, color=theme.primary, fill_opacity=0.7)
        lab = Text(labels[i] if labels else f"{v:.2g}", font_size=16, color=WHITE)
        g = VGroup(rect, lab).arrange(DOWN, buff=0.08)
        bars.add(g)
    bars.arrange(RIGHT, buff=0.35)
    return bars

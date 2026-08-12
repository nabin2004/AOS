"""Coordinate / axes helpers."""

from __future__ import annotations

from manim import Axes, NumberPlane

from manim_viz.theme import DEFAULT_THEME


def make_axes(
    x_range=(-4, 4, 1),
    y_range=(-3, 3, 1),
    x_length: float = 6.5,
    y_length: float = 4.0,
    scale: float = 0.85,
) -> Axes:
    return Axes(
        x_range=list(x_range),
        y_range=list(y_range),
        x_length=x_length,
        y_length=y_length,
        tips=False,
    ).scale(scale)


def make_plane(
    x_range=(-4, 4, 1),
    y_range=(-3, 3, 1),
    scale: float = 0.7,
) -> NumberPlane:
    return NumberPlane(
        x_range=list(x_range),
        y_range=list(y_range),
        background_line_style={"stroke_opacity": 0.35, "stroke_color": DEFAULT_THEME.soft},
    ).scale(scale)

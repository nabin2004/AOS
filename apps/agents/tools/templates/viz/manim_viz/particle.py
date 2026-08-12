"""Particle + trajectory trail for mechanics."""

from __future__ import annotations

from collections.abc import Sequence

from manim import Dot, VMobject, VGroup, WHITE

from manim_viz.theme import DEFAULT_THEME, VizTheme


def particle(point, *, radius: float = 0.12, color=None, theme: VizTheme | None = None) -> Dot:
    theme = theme or DEFAULT_THEME
    return Dot(point, radius=radius, color=color or theme.highlight)


def trajectory_curve(
    points: Sequence,
    *,
    color=None,
    theme: VizTheme | None = None,
) -> VMobject:
    """Smooth polyline through scene points."""
    theme = theme or DEFAULT_THEME
    color = color or theme.secondary
    path = VMobject(color=color, stroke_width=3)
    if len(points) >= 2:
        path.set_points_as_corners(list(points))
    return path


def particle_with_trail(
    points: Sequence,
    *,
    theme: VizTheme | None = None,
) -> VGroup:
    theme = theme or DEFAULT_THEME
    trail = trajectory_curve(points, theme=theme)
    dot = particle(points[-1] if points else (0, 0, 0), theme=theme)
    return VGroup(trail, dot)

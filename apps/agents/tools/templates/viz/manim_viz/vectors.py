"""Vector arrow primitives."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, Arrow, Dot, MathTex, Text, VGroup, WHITE

from manim_viz.theme import DEFAULT_THEME, VizTheme


def vector_arrow(
    start: Sequence[float],
    end: Sequence[float],
    *,
    color=None,
    label: str | None = None,
    theme: VizTheme | None = None,
) -> VGroup:
    """2D arrow from start→end in scene coordinates (already mapped)."""
    theme = theme or DEFAULT_THEME
    color = color or theme.primary
    arrow = Arrow(start, end, buff=0, color=color, stroke_width=4)
    tip = Dot(end, radius=0.05, color=color)
    group = VGroup(arrow, tip)
    if label:
        lab = MathTex(label, font_size=24, color=color)
        lab.next_to(arrow, DOWN, buff=0.1)
        group.add(lab)
    return group


def labeled_vector_on_plane(
    plane,
    components: Sequence[float],
    *,
    origin: Sequence[float] = (0.0, 0.0),
    color=None,
    label: str | None = None,
    theme: VizTheme | None = None,
) -> VGroup:
    theme = theme or DEFAULT_THEME
    color = color or theme.highlight
    ox, oy = origin
    vx, vy = components[0], components[1]
    start = plane.c2p(ox, oy)
    end = plane.c2p(ox + vx, oy + vy)
    return vector_arrow(start, end, color=color, label=label, theme=theme)

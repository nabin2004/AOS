"""Vector primitives: lines, polygons, curves, and canonical :class:`~motiongram.core.Circle`."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from motiongram.canvas import Canvas
from motiongram.core import Circle, Node

PathCommands = list[tuple[str, tuple[float, ...]]]


@dataclass(slots=True)
class Line(Node):
    """Line segment from start to end in local space.

    Use keyword arguments for geometry fields so positional args do not bind
    :class:`~motiongram.core.Node` fields ``x``, ``y``, ``children``.
    """

    x0: float = 0.0
    y0: float = 0.0
    x1: float = 100.0
    y1: float = 0.0
    stroke_color: str = "#FFFFFF"
    stroke_width: float = 2.0
    dash_pattern: tuple[float, ...] = ()

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        if stroke_line is not None:
            dp = self.dash_pattern if len(self.dash_pattern) >= 2 else None
            stroke_line(
                px + self.x0,
                py + self.y0,
                px + self.x1,
                py + self.y1,
                self.stroke_color,
                self.stroke_width,
                dash_pattern=dp,
            )


@dataclass(slots=True)
class Polygon(Node):
    """Closed polygon from vertex list."""

    vertices: tuple[tuple[float, float], ...] = ()
    fill_color: str = "#FFFFFF"
    stroke_color: str | None = None
    stroke_width: float = 0.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fill_polygon = getattr(canvas, "fill_polygon", None)
        if fill_polygon is not None and len(self.vertices) >= 3:
            fill_polygon(
                self.vertices,
                fill_color=self.fill_color,
                stroke_color=self.stroke_color,
                stroke_width=self.stroke_width,
                ox=px,
                oy=py,
            )


@dataclass(slots=True)
class BezierCurve(Node):
    """Cubic Bézier with control points ``p0…p3`` in local space."""

    p0: tuple[float, float] = (0.0, 0.0)
    p1: tuple[float, float] = (0.0, 0.0)
    p2: tuple[float, float] = (0.0, 0.0)
    p3: tuple[float, float] = (100.0, 0.0)
    stroke_color: str = "#FFFFFF"
    stroke_width: float = 2.0
    dash_pattern: tuple[float, ...] = ()

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "stroke_bezier", None)
        if fn is None:
            return
        dp = self.dash_pattern if len(self.dash_pattern) >= 2 else None
        fn(
            (px + self.p0[0], py + self.p0[1]),
            (px + self.p1[0], py + self.p1[1]),
            (px + self.p2[0], py + self.p2[1]),
            (px + self.p3[0], py + self.p3[1]),
            self.stroke_color,
            self.stroke_width,
            dash_pattern=dp,
        )


@dataclass(slots=True)
class Arc(Node):
    """Circular arc stroke centered at the node's anchor."""

    radius: float = 50.0
    start_angle: float = 0.0
    end_angle: float = math.pi
    stroke_color: str = "#FFFFFF"
    stroke_width: float = 2.0
    dash_pattern: tuple[float, ...] = ()

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "stroke_arc", None)
        if fn is None:
            return
        sweep = self.end_angle - self.start_angle
        dp = self.dash_pattern if len(self.dash_pattern) >= 2 else None
        fn(
            px,
            py,
            self.radius,
            self.start_angle,
            sweep,
            self.stroke_color,
            self.stroke_width,
            dash_pattern=dp,
        )


@dataclass(slots=True)
class Sector(Node):
    """Filled circular sector (pie wedge) centered at the node's anchor."""

    radius: float = 50.0
    start_angle: float = 0.0
    sweep_angle: float = math.pi / 2
    fill_color: str = "#FFFFFF"
    stroke_color: str | None = None
    stroke_width: float = 0.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "fill_sector", None)
        if fn is None:
            return
        fn(
            px,
            py,
            self.radius,
            self.start_angle,
            self.sweep_angle,
            fill_color=self.fill_color,
            stroke_color=self.stroke_color if self.stroke_width > 0 else None,
            stroke_width=self.stroke_width,
        )


@dataclass(slots=True)
class SemiCircle(Sector):
    """Half-disk; orient the flat diameter with ``start_angle``."""

    sweep_angle: float = math.pi


@dataclass(slots=True)
class Path(Node):
    """Piecewise path: commands ``M``, ``L``, ``C``, ``Z`` with local coordinates."""

    commands: PathCommands = field(default_factory=list)
    stroke_color: str = "#FFFFFF"
    stroke_width: float = 2.0
    fill_color: str | None = None
    dash_pattern: tuple[float, ...] = ()

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "stroke_path", None)
        if fn is None or not self.commands:
            return
        dp = self.dash_pattern if len(self.dash_pattern) >= 2 else None
        fn(
            self.commands,
            self.stroke_color,
            self.stroke_width,
            fill_color=self.fill_color,
            ox=px,
            oy=py,
            dash_pattern=dp,
        )


@dataclass(slots=True)
class Rectangle(Node):
    """Axis-aligned rectangle; anchor is top-left corner."""

    width: float = 100.0
    height: float = 50.0
    corner_radius: float = 0.0
    fill_color: str = "#FFFFFF"
    stroke_color: str | None = None
    stroke_width: float = 0.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "fill_round_rect", None)
        if fn is None:
            return
        left = px
        top = py
        right = px + self.width
        bottom = py + self.height
        r = max(0.0, self.corner_radius)
        fn(
            left,
            top,
            right,
            bottom,
            r,
            fill_color=self.fill_color,
            stroke_color=self.stroke_color if self.stroke_width > 0 else None,
            stroke_width=self.stroke_width,
        )


@dataclass(slots=True)
class Ellipse(Node):
    """Ellipse centered at the node's anchor."""

    rx: float = 50.0
    ry: float = 30.0
    fill_color: str = "#FFFFFF"
    stroke_color: str | None = None
    stroke_width: float = 0.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "fill_ellipse", None)
        if fn is None:
            return
        fn(
            px,
            py,
            self.rx,
            self.ry,
            fill_color=self.fill_color,
            stroke_color=self.stroke_color if self.stroke_width > 0 else None,
            stroke_width=self.stroke_width,
        )


@dataclass(slots=True)
class RegularPolygon(Node):
    """Regular ``n``-gon centered at the node's anchor."""

    sides: int = 6
    radius: float = 50.0
    phase: float = 0.0
    fill_color: str = "#FFFFFF"
    stroke_color: str | None = None
    stroke_width: float = 0.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        n = max(3, self.sides)
        verts: list[tuple[float, float]] = []
        for k in range(n):
            ang = self.phase + 2 * math.pi * k / n
            verts.append((self.radius * math.cos(ang), self.radius * math.sin(ang)))
        fill_polygon = getattr(canvas, "fill_polygon", None)
        if fill_polygon is not None:
            fill_polygon(
                tuple(verts),
                fill_color=self.fill_color,
                stroke_color=self.stroke_color,
                stroke_width=self.stroke_width,
                ox=px,
                oy=py,
            )


__all__ = [
    "Arc",
    "BezierCurve",
    "Circle",
    "Ellipse",
    "Line",
    "Path",
    "PathCommands",
    "Polygon",
    "Rectangle",
    "RegularPolygon",
    "Sector",
    "SemiCircle",
]

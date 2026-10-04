"""Composition overlays and layout helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable
from collections.abc import Sequence as ABCSequence

from motiongram.canvas import Canvas
from motiongram.core import Node

TAU = 2.0 * math.pi
PHI = (1.0 + math.sqrt(5.0)) / 2.0


def distribute_evenly(nodes: ABCSequence[Node], axis: str, start: float, end: float) -> None:
    """Assign ``node.x`` or ``node.y`` evenly between ``start`` and ``end`` (inclusive)."""
    vals = tuple(nodes)
    n = len(vals)
    if n == 0 or end <= start:
        return
    for i, node in enumerate(vals):
        coord = start + (end - start) * (i / max(1, n - 1))
        axis_l = axis.lower()
        if axis_l == "x":
            node.x = coord
        elif axis_l == "y":
            node.y = coord
        else:
            raise ValueError("axis must be 'x' or 'y'")


def stack_vertical(nodes: Iterable[Node], gap: float) -> None:
    """Place nodes one under another preserving order, anchored to first ``y``."""
    ys = tuple(nodes)
    if not ys:
        return
    y = ys[0].y
    for node in ys[1:]:
        y += gap
        node.y = y


def align(nodes: ABCSequence[Node], *, x: float | None = None, y: float | None = None) -> None:
    """Snap every node anchor to optional shared ``x`` and/or ``y``."""
    for n in nodes:
        if x is not None:
            n.x = x
        if y is not None:
            n.y = y


class RuleOfThirdsGrid(Node):
    """Two vertical + two horizontal guide lines dividing the plane into thirds."""

    __slots__ = ("width", "height", "color", "line_width")

    def __init__(
        self,
        *,
        width: float = 1280.0,
        height: float = 720.0,
        color: str = "#58647A88",
        line_width: float = 1.0,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(x=x, y=y)
        self.width = width
        self.height = height
        self.color = color
        self.line_width = line_width

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        if stroke_line is None:
            return
        xv1 = px + self.width / 3.0
        xv2 = px + 2.0 * self.width / 3.0
        yh1 = py + self.height / 3.0
        yh2 = py + 2.0 * self.height / 3.0
        for xv in (xv1, xv2):
            stroke_line(xv, py, xv, py + self.height, self.color, self.line_width)
        for yh in (yh1, yh2):
            stroke_line(px, yh, px + self.width, yh, self.color, self.line_width)


class GoldenSpiral(Node):
    """Logarithmic spiral overlay using short cubic segments."""

    __slots__ = ("loops", "a", "b", "segments", "color", "line_width")

    def __init__(
        self,
        *,
        loops: float = 2.75,
        a: float = 6.0,
        b: float = 0.25,
        segments: int = 80,
        color: str = "#D6B06899",
        line_width: float = 2.0,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(x=x, y=y)
        self.loops = loops
        self.a = a
        self.b = b
        self.segments = max(12, segments)
        self.color = color
        self.line_width = line_width

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_bezier = getattr(canvas, "stroke_bezier", None)
        if stroke_bezier is None:
            return
        pts: list[tuple[float, float]] = []
        n = self.segments
        for i in range(n + 1):
            theta = self.loops * TAU * (i / n)
            r = self.a * math.exp(self.b * theta)
            pts.append((r * math.cos(theta), r * math.sin(theta)))
        for i in range(0, len(pts) - 3, 3):
            p0 = pts[i]
            p1 = pts[i + 1]
            p2 = pts[i + 2]
            p3 = pts[i + 3]
            stroke_bezier(
                (px + p0[0], py + p0[1]),
                (px + p1[0], py + p1[1]),
                (px + p2[0], py + p2[1]),
                (px + p3[0], py + p3[1]),
                self.color,
                self.line_width,
            )


class GesturePath(Node):
    """Flowing Bézier ribbons approximating gesture lines."""

    __slots__ = ("control_points", "stroke_color", "stroke_width", "taper")

    def __init__(
        self,
        *,
        control_points: tuple[tuple[float, float], ...] = (),
        stroke_color: str = "#FF6B6B",
        stroke_width: float = 3.0,
        taper: bool = True,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(x=x, y=y)
        self.control_points = control_points
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.taper = taper

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        cps = self.control_points
        if len(cps) < 2:
            return
        stroke_bezier = getattr(canvas, "stroke_bezier", None)
        if stroke_bezier is None:
            return
        for i in range(len(cps) - 1):
            p0 = cps[max(0, i - 1)]
            p1 = cps[i]
            p2 = cps[i + 1]
            p3 = cps[min(len(cps) - 1, i + 2)]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0)
            width = self.stroke_width
            if self.taper:
                span = len(cps) - 1
                center = span / 2
                tt = abs(i - center) / max(center, 1e-6)
                width *= max(0.35, 1.0 - 0.6 * tt)
            stroke_bezier(
                (px + p1[0], py + p1[1]),
                (px + c1[0], py + c1[1]),
                (px + c2[0], py + c2[1]),
                (px + p2[0], py + p2[1]),
                self.stroke_color,
                width,
            )


__all__ = [
    "GoldenSpiral",
    "GesturePath",
    "PHI",
    "RuleOfThirdsGrid",
    "TAU",
    "align",
    "distribute_evenly",
    "stack_vertical",
]

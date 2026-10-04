"""Form primitives — lightweight 3D-ish shading without a full renderer."""

from __future__ import annotations

from dataclasses import dataclass

from motiongram.canvas import Canvas
from motiongram.core import Node


@dataclass(slots=True)
class Sphere(Node):
    """Radial-gradient disc suggesting a shaded sphere."""

    radius: float = 40.0
    highlight: str = "#F5F9FF"
    shadow: str = "#1A2744"
    mid: str = "#5F7AAF"

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "fill_radial_gradient_disc", None)
        if fn is None:
            return
        fn(
            px,
            py,
            self.radius,
            ((0.0, self.highlight), (0.45, self.mid), (1.0, self.shadow)),
        )


@dataclass(slots=True)
class Cube(Node):
    """Three visible facets approximating an isometric box."""

    size: float = 80.0
    face_top: str = "#6FA8DC"
    face_left: str = "#3F6CAC"
    face_right: str = "#2F4F7A"

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        s = self.size * 0.52
        u = self.size * 0.48
        v = self.size * 0.26
        # Right face — offset +u on X, slight vertical shear
        right = ((-s + u, -s - v), (s + u, -s), (s + u, s), (-s + u, s - v))
        # Left face — offset -u
        left = ((-s - u, -s - v), (-s + u, -s - v), (-s + u, s - v), (-s - u, s - v))
        # Top diamond
        top = ((-s, -s - v), (-s + u, -s - v), (s + u, -s), (s - u, -s - v * 2))
        fp = getattr(canvas, "fill_polygon", None)
        if fp is None:
            return
        fp(
            right,
            fill_color=self.face_right,
            stroke_color=self.face_right,
            stroke_width=0.5,
            ox=px,
            oy=py,
        )
        fp(
            left,
            fill_color=self.face_left,
            stroke_color=self.face_left,
            stroke_width=0.5,
            ox=px,
            oy=py,
        )
        fp(
            top,
            fill_color=self.face_top,
            stroke_color=self.face_top,
            stroke_width=0.5,
            ox=px,
            oy=py,
        )


@dataclass(slots=True)
class Cylinder(Node):
    """Cylinder with elliptical caps and flat side panel."""

    radius: float = 50.0
    height: float = 110.0
    body: str = "#5F8FE8"
    cap: str = "#9CC4FF"

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        ry = max(self.radius * 0.35, 2.5)
        half = self.height * 0.5
        top_y = -half
        bot_y = half
        ee = getattr(canvas, "fill_ellipse", None)
        fp = getattr(canvas, "fill_polygon", None)
        if ee is None or fp is None:
            return
        ee(
            px,
            py + top_y,
            self.radius,
            ry,
            fill_color=self.cap,
            stroke_color="#2B3F66",
            stroke_width=1.0,
        )
        side = (
            (-self.radius, top_y),
            (self.radius, top_y),
            (self.radius, bot_y),
            (-self.radius, bot_y),
        )
        fp(side, fill_color=self.body, stroke_color="#335EA6", stroke_width=0.8, ox=px, oy=py)
        ee(
            px,
            py + bot_y,
            self.radius,
            ry,
            fill_color=self.body,
            stroke_color="#24365A",
            stroke_width=1.0,
        )


__all__ = ["Cube", "Cylinder", "Sphere"]

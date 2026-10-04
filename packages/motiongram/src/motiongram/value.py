"""Value / lighting helpers."""

from __future__ import annotations

from dataclasses import dataclass

from motiongram.canvas import Canvas
from motiongram.core import Node


@dataclass(slots=True)
class GradientOverlay(Node):
    """Full-frame linear gradient slab in local bounding box."""

    width: float = 640.0
    height: float = 480.0
    angle_rad: float = 0.0
    stops: tuple[tuple[float, str], ...] = ((0.0, "#FFFFFF"), (1.0, "#000000"))

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "fill_linear_gradient_rect", None)
        if fn is None:
            return
        fn(px, py, px + self.width, py + self.height, self.stops, angle_rad=self.angle_rad)


@dataclass(slots=True)
class Shadow(Node):
    """Rounded drop-shadow placeholder using translucency (no Gaussian on ASCII)."""

    width: float = 120.0
    height: float = 40.0
    offset_x: float = 10.0
    offset_y: float = 10.0
    corner_radius: float = 14.0
    color: str = "#00000055"

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fn = getattr(canvas, "fill_round_rect", None)
        if fn is None:
            return
        left = px + self.offset_x
        top = py + self.offset_y
        fn(
            left,
            top,
            left + self.width,
            top + self.height,
            self.corner_radius,
            fill_color=self.color,
            stroke_color=None,
            stroke_width=0.0,
        )


__all__ = ["GradientOverlay", "Shadow"]

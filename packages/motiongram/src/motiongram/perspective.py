"""Perspective helpers."""

from __future__ import annotations

from dataclasses import dataclass

from motiongram.canvas import Canvas
from motiongram.core import Node


@dataclass(slots=True)
class PerspectiveGrid(Node):
    """Converging lines toward a horizon for perspective demonstrations."""

    width: float = 1280.0
    height: float = 720.0
    vanishing_x: float = 640.0
    horizon_y: float = 380.0
    num_radials: int = 18
    num_horizontals: int = 7
    color: str = "#3A4F65"
    line_width: float = 1.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        if stroke_line is None:
            return
        vx = px + self.vanishing_x
        hy = py + self.horizon_y
        bottom_y = py + self.height * 0.95
        for i in range(self.num_radials):
            frac = i / max(1, self.num_radials - 1)
            x_bottom = px + frac * self.width
            stroke_line(x_bottom, bottom_y, vx, hy, self.color, self.line_width)
        for j in range(1, self.num_horizontals + 1):
            t = j / (self.num_horizontals + 1)
            y_line = hy + (bottom_y - hy) * t ** 1.05
            # approximate horizontal intersecting radial bounds
            left_x = px + self.width * 0.08 + (vx - px) * 0.12 * (1 - t)
            right_x = px + self.width * 0.92 - (px + self.width - vx) * 0.12 * (1 - t)
            stroke_line(left_x, y_line, right_x, y_line, self.color, self.line_width * 0.7)


__all__ = ["PerspectiveGrid"]

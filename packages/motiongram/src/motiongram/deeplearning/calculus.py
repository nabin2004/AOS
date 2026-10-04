"""Visual components for calculus in deep learning."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from motiongram.core import Node
from motiongram.canvas import Canvas


def _quadratic(x: float) -> float:
    # y = (x - 2)^2 / 3 + 1
    return ((x - 150.0) ** 2) / 100.0 + 50.0


def _quadratic_deriv(x: float) -> float:
    return 2 * (x - 150.0) / 100.0


@dataclass(slots=True)
class Derivatives(Node):
    """Visualizes a math curve with a tangent line drawn at x_val."""

    x_val: float = 180.0  # Center is around 150
    curve_color: str = "#61afef"
    tangent_color: str = "#e5c07b"
    grid_color: str = "#2c313c"
    text_color: str = "#abb2bf"
    width: float = 300.0
    height: float = 200.0
    show_triangle: bool = True
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        draw_text = getattr(canvas, "draw_text", None)

        # Draw grid bounding box and axis guides
        if stroke_line is not None:
            # Border
            stroke_line(px, py, px + self.width, py, self.grid_color, 1.0)
            stroke_line(px, py + self.height, px + self.width, py + self.height, self.grid_color, 1.0)
            stroke_line(px, py, px, py + self.height, self.grid_color, 1.0)
            stroke_line(px + self.width, py, px + self.width, py + self.height, self.grid_color, 1.0)

            # Draw function curve (evaluate inside bounds)
            prev_x, prev_y = None, None
            for step in range(0, int(self.width), 4):
                cx = px + step
                # Transform local x to function space
                cy = py + self.height - _quadratic(step)
                if 0 <= (cy - py) <= self.height:
                    if prev_x is not None and prev_y is not None:
                        stroke_line(prev_x, prev_y, cx, cy, self.curve_color, 2.5)
                    prev_x, prev_y = cx, cy

            # Tangent line math
            tx = self.x_val
            ty = _quadratic(tx)
            slope = _quadratic_deriv(tx)

            # Draw tangent line segment
            dx = 60.0
            x0 = tx - dx
            y0 = ty - dx * slope
            x1 = tx + dx
            y1 = ty + dx * slope

            stroke_line(
                px + x0, py + self.height - y0,
                px + x1, py + self.height - y1,
                self.tangent_color, 2.0
            )

            # Draw a dot at the tangent point
            fill_ellipse = getattr(canvas, "fill_ellipse", None)
            if fill_ellipse is not None:
                fill_ellipse(
                    px + tx, py + self.height - ty,
                    5.0, 5.0,
                    fill_color=self.tangent_color,
                )

            # Draw Rise / Run right triangle
            if self.show_triangle:
                # Triangle corners: (tx, ty), (tx + dx/2, ty), (tx + dx/2, ty + (dx/2)*slope)
                tdx = 30.0
                tdy = tdx * slope
                # Bottom side (Run)
                stroke_line(
                    px + tx, py + self.height - ty,
                    px + tx + tdx, py + self.height - ty,
                    "#98c379", 1.5, dash_pattern=(2.0, 2.0)
                )
                # Right side (Rise)
                stroke_line(
                    px + tx + tdx, py + self.height - ty,
                    px + tx + tdx, py + self.height - (ty + tdy),
                    "#e06c75", 1.5, dash_pattern=(2.0, 2.0)
                )

        if draw_text is not None:
            # Labels
            draw_text("f(x)", px + 10.0, py + 10.0, self.font_size, self.curve_color)
            slope_val = _quadratic_deriv(self.x_val) / 10.0  # scaled for readability
            draw_text(f"Slope dy/dx = {slope_val:.2f}", px + 10.0, py + self.height - 20.0, self.font_size, self.tangent_color)


@dataclass(slots=True)
class Differentiation(Node):
    """Visualizes a secant line approaching a tangent line as h_val approaches 0."""

    x_val: float = 140.0
    h_val: float = 80.0  # Animating this from 80.0 to 1e-3 shows limit convergence
    curve_color: str = "#61afef"
    secant_color: str = "#e06c75"
    text_color: str = "#abb2bf"
    width: float = 300.0
    height: float = 200.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        fill_ellipse = getattr(canvas, "fill_ellipse", None)
        draw_text = getattr(canvas, "draw_text", None)

        if stroke_line is not None:
            # Draw curve
            prev_x, prev_y = None, None
            for step in range(0, int(self.width), 4):
                cx = px + step
                cy = py + self.height - _quadratic(step)
                if 0 <= (cy - py) <= self.height:
                    if prev_x is not None and prev_y is not None:
                        stroke_line(prev_x, prev_y, cx, cy, self.curve_color, 2.5)
                    prev_x, prev_y = cx, cy

            # Key points
            x0 = self.x_val
            y0 = _quadratic(x0)
            x1 = x0 + self.h_val
            y1 = _quadratic(x1)

            # Draw secant line connecting x0 and x1 (extended slightly)
            slope = (y1 - y0) / (x1 - x0) if abs(x1 - x0) > 1e-4 else _quadratic_deriv(x0)
            dx = 80.0
            lx0 = x0 - dx * 0.5
            ly0 = y0 - dx * 0.5 * slope
            lx1 = x1 + dx * 0.5
            ly1 = y1 + dx * 0.5 * slope

            stroke_line(
                px + lx0, py + self.height - ly0,
                px + lx1, py + self.height - ly1,
                self.secant_color, 2.0
            )

            # Draw point dots
            if fill_ellipse is not None:
                fill_ellipse(px + x0, py + self.height - y0, 5.0, 5.0, fill_color="#e5c07b")
                fill_ellipse(px + x1, py + self.height - y1, 5.0, 5.0, fill_color="#e06c75")

        if draw_text is not None:
            draw_text("Secant line (h -> 0 limit)", px + 10.0, py + 10.0, self.font_size, self.secant_color)
            draw_text(f"h = {self.h_val:.1f}", px + self.width - 80.0, py + 10.0, self.font_size, self.text_color)


@dataclass(slots=True)
class PartialDerivatives(Node):
    """Visualizes partial derivatives by drawing horizontal or vertical slices on a contour."""

    slice_axis: str = "x"  # "x" or "y"
    slice_coord: float = 100.0  # Center slice coordinate
    contour_color: str = "#2c313c"
    slice_color: str = "#e5c07b"
    slope_color: str = "#98c379"
    width: float = 240.0
    height: float = 240.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        fill_ellipse = getattr(canvas, "fill_ellipse", None)
        draw_text = getattr(canvas, "draw_text", None)

        cx, cy = px + self.width / 2.0, py + self.height / 2.0

        if stroke_line is not None:
            # Draw nested rings (contour landscape representation)
            for r in [30.0, 60.0, 90.0, 110.0]:
                if fill_ellipse is not None:
                    fill_ellipse(cx, cy, r, r * 0.7, fill_color="#00000000", stroke_color=self.contour_color, stroke_width=1.5)

            # Draw slice cutting plane line
            if self.slice_axis.lower() == "x":
                # horizontal cut: y = constant
                cut_y = cy - (self.slice_coord - self.height / 2.0) * 0.7
                stroke_line(px, cut_y, px + self.width, cut_y, self.slice_color, 2.0, dash_pattern=(4.0, 4.0))
            else:
                # vertical cut: x = constant
                cut_x = cx + (self.slice_coord - self.width / 2.0)
                stroke_line(cut_x, py, cut_x, py + self.height, self.slice_color, 2.0, dash_pattern=(4.0, 4.0))

            # Highlight slope arrow at intersection
            if fill_ellipse is not None:
                fill_ellipse(cx, cy, 6.0, 6.0, fill_color=self.slope_color)

        if draw_text is not None:
            axis_symbol = "dF/dx" if self.slice_axis.lower() == "x" else "dF/dy"
            draw_text(f"Partial derivative {axis_symbol}", px + 10.0, py - 10.0, self.font_size, self.slice_color)


@dataclass(slots=True)
class Gradients(Node):
    """Visualizes gradient descent steps descending down nested contour rings."""

    contour_rings: int = 5
    path: list[tuple[float, float]] = field(default_factory=list)  # list of (x, y) relative coordinates
    progress: float = 1.0  # 0 to 1 sweeps through drawing path segments
    contour_color: str = "#2c313c"
    path_color: str = "#e06c75"
    point_color: str = "#98c379"
    width: float = 300.0
    height: float = 300.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        fill_ellipse = getattr(canvas, "fill_ellipse", None)
        draw_text = getattr(canvas, "draw_text", None)

        cx, cy = px + self.width / 2.0, py + self.height / 2.0

        # Draw concentric nested contour ellipses
        if fill_ellipse is not None:
            for i in range(1, self.contour_rings + 1):
                rx = (self.width * 0.45) * (i / self.contour_rings)
                ry = (self.height * 0.35) * (i / self.contour_rings)
                fill_ellipse(cx, cy, rx, ry, fill_color="#00000000", stroke_color=self.contour_color, stroke_width=1.2)

        # Plot gradient path steps
        if self.path and stroke_line is not None:
            n_segments = len(self.path) - 1
            if n_segments >= 1:
                limit = int(self.progress * n_segments) if self.progress < 1.0 else n_segments
                # Draw past path steps
                for i in range(limit):
                    x0, y0 = self.path[i]
                    x1, y1 = self.path[i+1]
                    stroke_line(cx + x0, cy + y0, cx + x1, cy + y1, self.path_color, 2.5)

                    # Draw point dots
                    if fill_ellipse is not None:
                        fill_ellipse(cx + x0, cy + y0, 3.5, 3.5, fill_color=self.point_color)

                # Draw current progress interpolator
                if self.progress < 1.0 and limit < n_segments:
                    rem = (self.progress * n_segments) - limit
                    x0, y0 = self.path[limit]
                    x1, y1 = self.path[limit+1]
                    interp_x = x0 + (x1 - x0) * rem
                    interp_y = y0 + (y1 - y0) * rem
                    stroke_line(cx + x0, cy + y0, cx + interp_x, cy + interp_y, self.path_color, 2.5)
                    if fill_ellipse is not None:
                        fill_ellipse(cx + interp_x, cy + interp_y, 4.5, 4.5, fill_color=self.path_color)
                elif is_completed := (self.progress >= 1.0):
                    # End point highlight
                    last_x, last_y = self.path[-1]
                    if fill_ellipse is not None:
                        fill_ellipse(cx + last_x, cy + last_y, 6.0, 6.0, fill_color=self.path_color)

        if draw_text is not None:
            draw_text("Gradient Descent Loss Landscape", px + 10.0, py + self.height - 20.0, self.font_size, "#abb2bf")


@dataclass(slots=True)
class ChainRule(Node):
    """Visualizes Chain Rule chain composition and fraction multiplications."""

    variables: list[str] = field(default_factory=list)  # e.g., ["x", "y", "z"]
    derivatives: list[str] = field(default_factory=list)  # e.g., ["dy/dx", "dz/dy"]
    active_idx: int | None = None
    stroke_color: str = "#5c6370"
    active_color: str = "#61afef"
    font_size: float = 16.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        draw_text = getattr(canvas, "draw_text", None)
        stroke_line = getattr(canvas, "stroke_line", None)

        if not self.variables:
            return

        spacing = 130.0
        fill_round_rect = getattr(canvas, "fill_round_rect", None)

        # Draw variable node circles / boxes
        for i, var in enumerate(self.variables):
            cx = px + i * spacing
            cy = py

            is_active = (i == self.active_idx)
            box_color = self.active_color if is_active else self.stroke_color

            if fill_round_rect is not None:
                fill_round_rect(
                    cx - 25.0, cy - 25.0, cx + 25.0, cy + 25.0, 12.0,
                    fill_color="#21252b", stroke_color=box_color, stroke_width=2.0
                )

            if draw_text is not None:
                tx = cx - len(var) * (self.font_size * 0.3)
                ty = cy - self.font_size * 0.5
                draw_text(var, tx, ty, self.font_size, "#ffffff")

        # Draw connecting arrows and derivative fractions
        for i in range(len(self.variables) - 1):
            x0 = px + i * spacing + 25.0
            x1 = px + (i + 1) * spacing - 25.0
            cy = py

            is_active_deriv = (self.active_idx is not None and (i == self.active_idx or i == self.active_idx - 1))
            line_color = self.active_color if is_active_deriv else self.stroke_color

            if stroke_line is not None:
                # Arrow line
                stroke_line(x0, cy, x1, cy, line_color, 2.0)
                # Simple arrow tip
                stroke_line(x1 - 6.0, cy - 6.0, x1, cy, line_color, 2.0)
                stroke_line(x1 - 6.0, cy + 6.0, x1, cy, line_color, 2.0)

            # Draw fraction label above arrow
            if i < len(self.derivatives) and draw_text is not None:
                deriv_label = self.derivatives[i]
                lx = (x0 + x1) / 2.0 - len(deriv_label) * (self.font_size * 0.28)
                ly = cy - 30.0
                draw_text(deriv_label, lx, ly, self.font_size * 0.9, line_color)

        # Draw final equation below
        if len(self.variables) >= 3 and len(self.derivatives) >= 2 and draw_text is not None:
            eq_y = py + 80.0
            first_var = self.variables[0]
            last_var = self.variables[-1]
            global_deriv = f"d{last_var}/d{first_var}"

            chain_terms = [f"d{self.variables[i+1]}/d{self.variables[i]}" for i in reversed(range(len(self.variables) - 1))]
            equation = f"{global_deriv} = " + " * ".join(chain_terms)

            draw_text(equation, px, eq_y, self.font_size * 1.1, self.active_color)
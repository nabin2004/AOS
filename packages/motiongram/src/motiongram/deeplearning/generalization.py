"""Visual components for error, generalization, and model selection."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from motiongram.core import Node
from motiongram.canvas import Canvas
from motiongram.deeplearning._draw import (
    DLTheme,
    draw_dot,
    draw_label,
    draw_plot_border,
    draw_polyline,
    draw_round_cell,
    format_float,
)


def _normalize_points(
    points: list[tuple[float, float]],
    width: float,
    height: float,
    *,
    pad: float = 12.0,
) -> list[tuple[float, float]]:
    if not points:
        return []
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_span = x_max - x_min or 1.0
    y_span = y_max - y_min or 1.0
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad
    return [
        (
            pad + (x - x_min) / x_span * inner_w,
            pad + inner_h - (y - y_min) / y_span * inner_h,
        )
        for x, y in points
    ]


def _default_loss_curve(n: int = 12) -> list[tuple[float, float]]:
    return [(float(i), 1.0 / (1.0 + 0.35 * i) + 0.08 * math.exp(-i * 0.3)) for i in range(n)]


def _poly_y(x: float, coeffs: list[float]) -> float:
    y = 0.0
    p = 1.0
    for c in coeffs:
        y += c * p
        p *= x
    return y


@dataclass(slots=True)
class Error(Node):
    """Simple meter/gauge for a scalar error in ``[0, 1]``."""

    value: float = 0.5
    label: str = "Error"
    width: float = 220.0
    height: float = 28.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        v = max(0.0, min(1.0, self.value))
        draw_label(canvas, self.label, px, py - self.font_size - 6.0, font_size=self.font_size, color=DLTheme.TEXT)

        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        stroke_line = getattr(canvas, "stroke_line", None)

        if fill_round_rect is not None:
            fill_round_rect(px, py, px + self.width, py + self.height, 6.0, fill_color=DLTheme.BG_DEEP, stroke_color=DLTheme.GRID, stroke_width=1.0)
            fill_round_rect(px, py, px + self.width * v, py + self.height, 6.0, fill_color=DLTheme.RED if v > 0.7 else (DLTheme.YELLOW if v > 0.35 else DLTheme.GREEN), stroke_color=None, stroke_width=0.0)

        if stroke_line is not None:
            tick_x = px + self.width * v
            stroke_line(tick_x, py - 4.0, tick_x, py + self.height + 4.0, DLTheme.HIGHLIGHT, 2.0)

        draw_label(canvas, format_float(v, precision=2), px + self.width + 10.0, py + (self.height - self.font_size) / 2.0, font_size=self.font_size, color=DLTheme.TEXT)


@dataclass(slots=True)
class TrainingError(Node):
    """Training loss curve that decreases over epochs."""

    loss_points: list[tuple[float, float]] = field(default_factory=_default_loss_curve)
    progress: float = 1.0
    label: str = "Training loss"
    width: float = 280.0
    height: float = 160.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        draw_label(canvas, self.label, px, py - self.font_size - 6.0, font_size=self.font_size, color=DLTheme.RED)
        draw_plot_border(canvas, px, py, self.width, self.height)

        pts = _normalize_points(self.loss_points, self.width, self.height)
        if not pts:
            return

        n = len(pts) - 1
        limit = int(self.progress * n) if self.progress < 1.0 else n
        visible = pts[: limit + 1]
        draw_polyline(canvas, [(px + x, py + y) for x, y in visible], color=DLTheme.RED, width=2.5)

        if visible:
            draw_dot(canvas, px + visible[-1][0], py + visible[-1][1], color=DLTheme.HIGHLIGHT, radius=5.0)

        draw_label(canvas, "epoch →", px + self.width - 52.0, py + self.height + 8.0, font_size=self.font_size * 0.85, color=DLTheme.TEXT_DIM)


@dataclass(slots=True)
class GeneralizationError(Node):
    """Train vs test loss curves showing the generalization gap."""

    train_points: list[tuple[float, float]] = field(default_factory=_default_loss_curve)
    test_points: list[tuple[float, float]] = field(default_factory=list)
    progress: float = 1.0
    width: float = 300.0
    height: float = 170.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        test_pts = self.test_points
        if not test_pts and self.train_points:
            test_pts = [(x, y * 1.15 + 0.06 + 0.02 * math.sin(x)) for x, y in self.train_points]

        draw_label(canvas, "Generalization gap", px, py - self.font_size - 6.0, font_size=self.font_size, color=DLTheme.TEXT)
        draw_plot_border(canvas, px, py, self.width, self.height)

        train = _normalize_points(self.train_points, self.width, self.height)
        test = _normalize_points(test_pts, self.width, self.height)
        n = max(len(train), len(test)) - 1
        limit = int(self.progress * n) if self.progress < 1.0 else n

        if train:
            draw_polyline(canvas, [(px + x, py + y) for x, y in train[: limit + 1]], color=DLTheme.BLUE, width=2.0)
        if test:
            draw_polyline(canvas, [(px + x, py + y) for x, y in test[: limit + 1]], color=DLTheme.PURPLE, width=2.0)

        if train and test and limit >= 0:
            i = min(limit, len(train) - 1, len(test) - 1)
            tx0, ty0 = train[i]
            tx1, ty1 = test[i]
            stroke_line = getattr(canvas, "stroke_line", None)
            if stroke_line is not None:
                stroke_line(px + tx0, py + ty0, px + tx1, py + ty1, DLTheme.YELLOW, 1.5, dash_pattern=(3.0, 3.0))

        draw_label(canvas, "train", px + 8.0, py + 8.0, font_size=self.font_size * 0.9, color=DLTheme.BLUE)
        draw_label(canvas, "test", px + 52.0, py + 8.0, font_size=self.font_size * 0.9, color=DLTheme.PURPLE)


@dataclass(slots=True)
class Underfitting(Node):
    """Scatter data with a straight line fit and visibly high residual error."""

    points: list[tuple[float, float]] = field(default_factory=list)
    slope: float = 0.45
    intercept: float = 0.2
    progress: float = 1.0
    label: str = "Underfitting"
    width: float = 260.0
    height: float = 200.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        pts = self.points
        if not pts:
            pts = [(0.1 + 0.12 * i, 0.15 + 0.1 * i + 0.08 * math.sin(i)) for i in range(8)]

        draw_label(canvas, self.label, px, py - self.font_size - 6.0, font_size=self.font_size, color=DLTheme.YELLOW)
        draw_plot_border(canvas, px, py, self.width, self.height)

        norm = _normalize_points(pts, self.width, self.height)
        for x, y in norm:
            draw_dot(canvas, px + x, py + y, color=DLTheme.CYAN, radius=4.5)

        x0, x1 = 12.0, self.width - 12.0
        y0 = self.height - (self.intercept * (self.height - 24.0) + 12.0)
        y1 = self.height - ((self.slope * 1.0 + self.intercept) * (self.height - 24.0) + 12.0)
        line_pts = [(x0, y0), (x1, y1)]
        n_seg = 1
        limit = int(self.progress * n_seg) if self.progress < 1.0 else n_seg
        draw_polyline(canvas, [(px + x, py + y) for x, y in line_pts[: limit + 1]], color=DLTheme.GREEN, width=2.0)

        mse = 0.0
        for x_raw, y_raw in pts:
            pred = self.slope * x_raw + self.intercept
            mse += (y_raw - pred) ** 2
        mse /= max(len(pts), 1)
        draw_label(canvas, f"high error ≈ {format_float(mse, precision=2)}", px, py + self.height + 10.0, color=DLTheme.RED, font_size=self.font_size)


@dataclass(slots=True)
class Overfitting(Node):
    """Scatter data with a wiggly high-degree polynomial that tracks noise."""

    points: list[tuple[float, float]] = field(default_factory=list)
    poly_coeffs: list[float] = field(default_factory=lambda: [0.1, -0.8, 2.5, -1.2, 0.4])
    progress: float = 1.0
    label: str = "Overfitting"
    width: float = 260.0
    height: float = 200.0
    font_size: float = 13.0
    curve_steps: int = 40

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        pts = self.points
        if not pts:
            pts = [(0.05 + 0.11 * i, 0.2 + 0.15 * i + 0.12 * math.sin(2.5 * i)) for i in range(9)]

        draw_label(canvas, self.label, px, py - self.font_size - 6.0, font_size=self.font_size, color=DLTheme.PURPLE)
        draw_plot_border(canvas, px, py, self.width, self.height)

        norm = _normalize_points(pts, self.width, self.height)
        for x, y in norm:
            draw_dot(canvas, px + x, py + y, color=DLTheme.CYAN, radius=4.5)

        xs = [p[0] for p in pts]
        x_min, x_max = min(xs), max(xs)
        raw_curve = [
            (x_min + (x_max - x_min) * i / max(self.curve_steps - 1, 1), _poly_y(x_min + (x_max - x_min) * i / max(self.curve_steps - 1, 1), self.poly_coeffs))
            for i in range(self.curve_steps)
        ]
        curve = _normalize_points(raw_curve, self.width, self.height)
        n = len(curve) - 1
        limit = int(self.progress * n) if self.progress < 1.0 else n
        draw_polyline(canvas, [(px + x, py + y) for x, y in curve[: limit + 1]], color=DLTheme.PURPLE, width=2.5)

        draw_label(canvas, "low train error, poor test", px, py + self.height + 10.0, color=DLTheme.PURPLE, font_size=self.font_size)


@dataclass(slots=True)
class ModelSelection(Node):
    """Train/validation/test split boxes plus a hyperparameter search grid."""

    train_fraction: float = 0.6
    val_fraction: float = 0.2
    test_fraction: float = 0.2
    grid_rows: int = 3
    grid_cols: int = 4
    active_cell: tuple[int, int] = (1, 2)
    progress: float = 0.0
    label: str = "Model selection"
    box_width: float = 72.0
    box_height: float = 44.0
    cell_size: float = 36.0
    gap: float = 4.0
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        draw_label(canvas, self.label, px, py - self.font_size - 6.0, font_size=self.font_size * 1.05, color=DLTheme.TEXT)

        splits = [
            ("train", self.train_fraction, DLTheme.GREEN),
            ("val", self.val_fraction, DLTheme.YELLOW),
            ("test", self.test_fraction, DLTheme.PURPLE),
        ]
        bx = px
        for name, frac, color in splits:
            w = self.box_width * frac * 3.2
            draw_round_cell(canvas, bx, py, w, label=f"{name}\n{int(frac * 100)}%", fill_color=DLTheme.BG, stroke_color=color, text_color=color, font_size=self.font_size - 1.0, radius=5.0)
            bx += w + 8.0

        gy = py + self.box_height + 28.0
        draw_label(canvas, "hyperparameter grid", px, gy - 18.0, font_size=self.font_size, color=DLTheme.TEXT_DIM)

        p = max(0.0, min(1.0, self.progress))
        total_cells = self.grid_rows * self.grid_cols
        scanned = int(p * total_cells) if p < 1.0 else total_cells

        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                idx = r * self.grid_cols + c
                cx = px + c * (self.cell_size + self.gap)
                cy = gy + r * (self.cell_size + self.gap)
                is_active = (r, c) == self.active_cell
                is_scanned = idx < scanned
                fill = DLTheme.HIGHLIGHT if is_active else (DLTheme.BG if is_scanned else DLTheme.BG_DEEP)
                stroke = DLTheme.GLOW if is_active else (DLTheme.CYAN if is_scanned else DLTheme.GRID)
                lr = 10 ** (-(r + 2))
                wd = 0.01 * (c + 1)
                draw_round_cell(
                    canvas,
                    cx,
                    cy,
                    self.cell_size,
                    label=f"η={lr:.0e}" if is_active or is_scanned else "",
                    fill_color=fill,
                    stroke_color=stroke,
                    text_color=DLTheme.BG_DEEP if is_active else DLTheme.TEXT_DIM,
                    font_size=self.font_size - 2.0,
                    radius=3.0,
                )

        if p >= 0.99:
            ar, ac = self.active_cell
            draw_label(
                canvas,
                f"best: lr≈{10 ** (-(ar + 2)):.0e}, wd={0.01 * (ac + 1):.2f}",
                px,
                gy + self.grid_rows * (self.cell_size + self.gap) + 8.0,
                font_size=self.font_size,
                color=DLTheme.GREEN,
            )

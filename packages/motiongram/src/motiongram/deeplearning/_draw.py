"""Shared drawing helpers and theme colors for deep-learning visual nodes."""

from __future__ import annotations

import math
from typing import Any

from motiongram.canvas import Canvas


class DLTheme:
    """Premium dark-mode palette for explainer visuals."""

    BG = "#21252b"
    BG_DEEP = "#282c34"
    TEXT = "#abb2bf"
    TEXT_DIM = "#5c6370"
    BLUE = "#61afef"
    CYAN = "#56b6c2"
    GREEN = "#98c379"
    YELLOW = "#e5c07b"
    PURPLE = "#c678dd"
    RED = "#e06c75"
    GRID = "#2c313c"
    HIGHLIGHT = "#e5c07b"
    GLOW = "#528bff"


def draw_round_cell(
    canvas: Canvas,
    x: float,
    y: float,
    size: float,
    *,
    label: str = "",
    fill_color: str = DLTheme.BG,
    stroke_color: str = DLTheme.CYAN,
    stroke_width: float = 1.5,
    text_color: str = DLTheme.TEXT,
    font_size: float = 14.0,
    radius: float = 6.0,
) -> None:
    """Draw a rounded cell with optional centered label."""
    fill_round_rect = getattr(canvas, "fill_round_rect", None)
    draw_text = getattr(canvas, "draw_text", None)
    if fill_round_rect is not None:
        fill_round_rect(
            x,
            y,
            x + size,
            y + size,
            radius,
            fill_color=fill_color,
            stroke_color=stroke_color if stroke_width > 0 else None,
            stroke_width=stroke_width,
        )
    if label and draw_text is not None:
        tx = x + (size - len(label) * (font_size * 0.55)) / 2.0
        ty = y + (size - font_size) / 2.0
        draw_text(label, tx, ty, font_size, text_color)


def draw_label(
    canvas: Canvas,
    text: str,
    x: float,
    y: float,
    *,
    font_size: float = 14.0,
    color: str = DLTheme.TEXT,
) -> None:
    draw_text = getattr(canvas, "draw_text", None)
    if draw_text is not None and text:
        draw_text(text, x, y, font_size, color)


def draw_arrow(
    canvas: Canvas,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    color: str = DLTheme.TEXT_DIM,
    width: float = 2.0,
    dash: tuple[float, ...] | None = None,
) -> None:
    stroke_line = getattr(canvas, "stroke_line", None)
    if stroke_line is None:
        return
    dp = dash if dash is not None and len(dash) >= 2 else None
    stroke_line(x0, y0, x1, y1, color, width, dash_pattern=dp)
    angle = math.atan2(y1 - y0, x1 - x0)
    tip = 8.0
    a1 = angle + math.pi * 0.82
    a2 = angle - math.pi * 0.82
    stroke_line(x1, y1, x1 + tip * math.cos(a1), y1 + tip * math.sin(a1), color, width)
    stroke_line(x1, y1, x1 + tip * math.cos(a2), y1 + tip * math.sin(a2), color, width)


def draw_plot_border(
    canvas: Canvas,
    px: float,
    py: float,
    width: float,
    height: float,
    *,
    color: str = DLTheme.GRID,
) -> None:
    stroke_line = getattr(canvas, "stroke_line", None)
    if stroke_line is None:
        return
    stroke_line(px, py, px + width, py, color, 1.0)
    stroke_line(px, py + height, px + width, py + height, color, 1.0)
    stroke_line(px, py, px, py + height, color, 1.0)
    stroke_line(px + width, py, px + width, py + height, color, 1.0)


def draw_polyline(
    canvas: Canvas,
    points: list[tuple[float, float]],
    *,
    color: str = DLTheme.BLUE,
    width: float = 2.0,
) -> None:
    stroke_line = getattr(canvas, "stroke_line", None)
    if stroke_line is None or len(points) < 2:
        return
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        stroke_line(x0, y0, x1, y1, color, width)


def draw_dot(
    canvas: Canvas,
    x: float,
    y: float,
    *,
    radius: float = 4.0,
    color: str = DLTheme.YELLOW,
) -> None:
    fill_ellipse = getattr(canvas, "fill_ellipse", None)
    if fill_ellipse is not None:
        fill_ellipse(x, y, radius, radius, fill_color=color)


def draw_grid_cells(
    canvas: Canvas,
    px: float,
    py: float,
    rows: int,
    cols: int,
    *,
    cell_size: float = 24.0,
    gap: float = 2.0,
    values: list[list[Any]] | None = None,
    highlight: set[tuple[int, int]] | None = None,
    fill_color: str = DLTheme.BG,
    stroke_color: str = DLTheme.GRID,
    highlight_color: str = DLTheme.HIGHLIGHT,
    font_size: float = 11.0,
) -> None:
    """Draw a rows x cols grid of cells with optional values and highlights."""
    hl = highlight or set()
    for r in range(rows):
        for c in range(cols):
            cx = px + c * (cell_size + gap)
            cy = py + r * (cell_size + gap)
            is_hl = (r, c) in hl
            label = ""
            if values and r < len(values) and c < len(values[r]):
                val = values[r][c]
                label = f"{val:.1f}" if isinstance(val, float) else str(val)
            draw_round_cell(
                canvas,
                cx,
                cy,
                cell_size,
                label=label,
                fill_color=highlight_color if is_hl else fill_color,
                stroke_color=stroke_color,
                text_color=DLTheme.BG_DEEP if is_hl else DLTheme.TEXT,
                font_size=font_size,
                radius=3.0,
            )


def format_float(val: float | int, *, precision: int = 1) -> str:
    if isinstance(val, float):
        return f"{val:.{precision}f}"
    return str(val)

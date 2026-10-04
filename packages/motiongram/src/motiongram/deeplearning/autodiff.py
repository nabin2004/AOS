"""Automatic differentiation visual components (tape, dual numbers, mode comparison)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from motiongram.core import Node
from motiongram.canvas import Canvas
from motiongram.deeplearning._draw import (
    DLTheme,
    draw_arrow,
    draw_label,
    draw_round_cell,
    format_float,
)


ModeLabel = Literal["forward", "backward"]


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _active_from_progress(n: int, progress: float) -> int:
    """Map progress in [0, 1] to an index in [0, n-1] for highlight sweep."""
    if n <= 0:
        return 0
    if progress >= 1.0:
        return n - 1
    return min(int(_clamp01(progress) * n), n - 1)


@dataclass(slots=True)
class ComputationTape(Node):
    """Vertical tape of named variables with values and gradients.

    ``mode`` labels whether the tape is shown in forward or reverse (backward) mode.
    ``active_idx`` highlights the current row; ``progress`` can drive a sweeping highlight.
    """

    variables: list[tuple[str, float, float]] = field(
        default_factory=lambda: [
            ("x", 2.0, 0.0),
            ("w", 3.0, 0.0),
            ("b", 1.0, 0.0),
            ("z", 7.0, 0.0),
            ("loss", 49.0, 1.0),
        ]
    )
    mode: ModeLabel = "forward"
    active_idx: int = 0
    progress: float = 0.0
    width: float = 280.0
    row_height: float = 36.0
    gap: float = 4.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        n = len(self.variables)
        if n == 0:
            return

        sweep_idx = _active_from_progress(n, self.progress)
        highlight_idx = self.active_idx if self.progress <= 0.0 else sweep_idx
        highlight_idx = max(0, min(highlight_idx, n - 1))

        mode_text = "Forward mode" if self.mode == "forward" else "Reverse mode"
        mode_color = DLTheme.BLUE if self.mode == "forward" else DLTheme.PURPLE
        draw_label(canvas, mode_text, px, py - self.font_size - 8.0, font_size=self.font_size, color=mode_color)

        col_w = (self.width - 2 * self.gap) / 3.0
        headers = ("name", "value", "grad")
        header_colors = (DLTheme.TEXT_DIM, DLTheme.CYAN, DLTheme.GREEN)
        for i, (hdr, hc) in enumerate(zip(headers, header_colors, strict=True)):
            draw_label(
                canvas,
                hdr,
                px + i * (col_w + self.gap),
                py,
                font_size=self.font_size * 0.85,
                color=hc,
            )

        body_y = py + self.font_size + 6.0
        fill_round_rect = getattr(canvas, "fill_round_rect", None)

        for row, (name, val, grad) in enumerate(self.variables):
            ry = body_y + row * (self.row_height + self.gap)
            is_active = row == highlight_idx
            row_stroke = DLTheme.HIGHLIGHT if is_active else DLTheme.GRID

            if fill_round_rect is not None:
                fill_round_rect(
                    px,
                    ry,
                    px + self.width,
                    ry + self.row_height,
                    5.0,
                    fill_color=DLTheme.GLOW if is_active else DLTheme.BG_DEEP,
                    stroke_color=row_stroke,
                    stroke_width=2.0 if is_active else 1.0,
                )

            cells = (
                name,
                format_float(val, precision=2),
                format_float(grad, precision=2),
            )
            text_colors = (DLTheme.TEXT, DLTheme.CYAN, DLTheme.GREEN)
            for col, (text, tc) in enumerate(zip(cells, text_colors, strict=True)):
                cx = px + col * (col_w + self.gap) + 8.0
                cy = ry + (self.row_height - self.font_size) / 2.0
                draw_label(
                    canvas,
                    text,
                    cx,
                    cy,
                    font_size=self.font_size,
                    color=tc if not is_active else DLTheme.BG_DEEP,
                )

            if is_active:
                draw_label(
                    canvas,
                    "▶",
                    px - 14.0,
                    ry + (self.row_height - self.font_size) / 2.0,
                    font_size=self.font_size,
                    color=DLTheme.HIGHLIGHT,
                )


@dataclass(slots=True)
class DualNumberNode(Node):
    """Rounded box showing a dual number ``val + ε·deriv`` with an optional operator."""

    val: float = 1.0
    deriv: float = 0.0
    operator: str = ""
    label: str = ""
    width: float = 120.0
    height: float = 52.0
    font_size: float = 14.0
    highlighted: bool = False

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if self.label:
            draw_label(
                canvas,
                self.label,
                px,
                py - self.font_size - 4.0,
                font_size=self.font_size * 0.9,
                color=DLTheme.TEXT_DIM,
            )

        stroke = DLTheme.HIGHLIGHT if self.highlighted else DLTheme.CYAN
        fill = DLTheme.GLOW if self.highlighted else DLTheme.BG
        dual_str = f"{format_float(self.val, precision=2)} + ε·{format_float(self.deriv, precision=2)}"

        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        if fill_round_rect is not None:
            fill_round_rect(
                px,
                py,
                px + self.width,
                py + self.height,
                8.0,
                fill_color=fill,
                stroke_color=stroke,
                stroke_width=2.0 if self.highlighted else 1.5,
            )

        draw_label(
            canvas,
            dual_str,
            px + 8.0,
            py + (self.height - self.font_size) / 2.0,
            font_size=self.font_size * 0.85,
            color=DLTheme.BG_DEEP if self.highlighted else DLTheme.CYAN,
        )

        if self.operator:
            op_x = px + self.width + 10.0
            op_y = py + (self.height - self.font_size * 1.2) / 2.0
            draw_round_cell(
                canvas,
                op_x,
                op_y,
                self.font_size * 1.6,
                label=self.operator,
                fill_color=DLTheme.BG_DEEP,
                stroke_color=DLTheme.YELLOW,
                text_color=DLTheme.YELLOW,
                font_size=self.font_size,
                radius=4.0,
            )


@dataclass(slots=True)
class TapeVisualizer(Node):
    """Side-by-side forward and reverse-mode tape passes with synchronized highlight sweep."""

    variables: list[tuple[str, float, float]] = field(
        default_factory=lambda: [
            ("x", 2.0, 0.0),
            ("w", 3.0, 0.0),
            ("z", 7.0, 0.0),
            ("loss", 49.0, 1.0),
        ]
    )
    progress: float = 0.0
    tape_width: float = 240.0
    gap_between: float = 48.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        draw_label(
            canvas,
            "Autodiff tape — mode comparison",
            px,
            py - self.font_size - 10.0,
            font_size=self.font_size + 1.0,
            color=DLTheme.TEXT,
        )

        n = len(self.variables)
        fwd_idx = _active_from_progress(n, self.progress)
        rev_idx = n - 1 - _active_from_progress(n, self.progress)

        fwd_tape = ComputationTape(
            variables=list(self.variables),
            mode="forward",
            active_idx=fwd_idx,
            progress=self.progress,
            width=self.tape_width,
            font_size=self.font_size,
        )
        fwd_tape.draw_world(canvas, px, py + 8.0)

        rev_x = px + self.tape_width + self.gap_between
        rev_vars = [
            (name, val, (grad if i <= rev_idx else 0.0))
            for i, (name, val, grad) in enumerate(self.variables)
        ]
        if rev_vars:
            last = rev_vars[-1]
            rev_vars[-1] = (last[0], last[1], 1.0)

        rev_tape = ComputationTape(
            variables=rev_vars,
            mode="backward",
            active_idx=rev_idx,
            progress=self.progress,
            width=self.tape_width,
            font_size=self.font_size,
        )
        rev_tape.draw_world(canvas, rev_x, py + 8.0)

        row_h = fwd_tape.row_height + fwd_tape.gap
        body_off = fwd_tape.font_size + 14.0
        y_fwd = py + 8.0 + body_off + fwd_idx * row_h + fwd_tape.row_height / 2.0
        y_rev = py + 8.0 + body_off + rev_idx * row_h + fwd_tape.row_height / 2.0
        draw_arrow(
            canvas,
            px + self.tape_width,
            y_fwd,
            rev_x,
            y_rev,
            color=DLTheme.TEXT_DIM,
            width=1.5,
            dash=(4.0, 4.0),
        )

        graph_y = py - 6.0
        node_w = 28.0
        for i, (name, _, _) in enumerate(self.variables):
            nx_fwd = px + 20.0 + i * (self.tape_width - 40.0) / max(n - 1, 1)
            nx_rev = rev_x + 20.0 + (n - 1 - i) * (self.tape_width - 40.0) / max(n - 1, 1)
            hl_fwd = i == fwd_idx
            hl_rev = i == rev_idx
            draw_round_cell(
                canvas,
                nx_fwd - node_w / 2.0,
                graph_y,
                node_w,
                label=name[:3],
                fill_color=DLTheme.GLOW if hl_fwd else DLTheme.BG_DEEP,
                stroke_color=DLTheme.HIGHLIGHT if hl_fwd else DLTheme.BLUE,
                font_size=10.0,
                radius=4.0,
            )
            draw_round_cell(
                canvas,
                nx_rev - node_w / 2.0,
                graph_y,
                node_w,
                label=name[:3],
                fill_color=DLTheme.GLOW if hl_rev else DLTheme.BG_DEEP,
                stroke_color=DLTheme.HIGHLIGHT if hl_rev else DLTheme.PURPLE,
                font_size=10.0,
                radius=4.0,
            )
            if i < n - 1:
                x_next = px + 20.0 + (i + 1) * (self.tape_width - 40.0) / max(n - 1, 1)
                draw_arrow(
                    canvas,
                    nx_fwd + node_w / 2.0,
                    graph_y + node_w / 2.0,
                    x_next - node_w / 2.0,
                    graph_y + node_w / 2.0,
                    color=DLTheme.BLUE,
                    width=1.2,
                )
                x_prev = rev_x + 20.0 + (n - 2 - i) * (self.tape_width - 40.0) / max(n - 1, 1)
                draw_arrow(
                    canvas,
                    nx_rev + node_w / 2.0,
                    graph_y + node_w / 2.0,
                    x_prev - node_w / 2.0,
                    graph_y + node_w / 2.0,
                    color=DLTheme.PURPLE,
                    width=1.2,
                )

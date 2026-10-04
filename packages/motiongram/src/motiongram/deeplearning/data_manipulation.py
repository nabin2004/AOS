"""Visual components for NumPy-style data manipulation in deep learning."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, cast

from motiongram.core import Node
from motiongram.canvas import Canvas
from motiongram.deeplearning._draw import (
    DLTheme,
    draw_arrow,
    draw_grid_cells,
    draw_label,
    draw_round_cell,
    format_float,
)
from motiongram.deeplearning.linear_algebra import Matrices, Vectors


def _matrix_dims(values: list[list[Any]]) -> tuple[int, int]:
    if not values or not values[0]:
        return 0, 0
    return len(values), len(values[0])


def _is_vector(values: list[list[Any]] | list[Any]) -> bool:
    if not values:
        return False
    if isinstance(values[0], (list, tuple)):
        return False
    return True


def _as_matrix(values: list[list[Any]] | list[Any]) -> list[list[Any]]:
    if not values:
        return []
    if _is_vector(values):
        return [cast(list[Any], list(values))]
    return cast(list[list[Any]], values)


def _elementwise(
    a: list[list[Any]],
    b: list[list[Any]],
    op: str,
) -> list[list[Any]]:
    rows, cols = _matrix_dims(a)
    out: list[list[Any]] = []
    for r in range(rows):
        row: list[Any] = []
        for c in range(cols):
            va, vb = a[r][c], b[r][c]
            if op == "+":
                row.append(float(va) + float(vb))
            elif op == "*":
                row.append(float(va) * float(vb))
            else:
                row.append(0.0)
        out.append(row)
    return out


@dataclass(slots=True)
class Indexing(Node):
    """Highlight a single matrix index with syntax label (e.g. ``x[1, 2]``)."""

    values: list[list[float | int]] = field(default_factory=list)
    index_row: int = 0
    index_col: int = 0
    name: str = "x"
    syntax: str = ""
    cell_size: float = 40.0
    gap: float = 3.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        rows, cols = _matrix_dims(self.values)
        if rows == 0:
            return

        r = max(0, min(self.index_row, rows - 1))
        c = max(0, min(self.index_col, cols - 1))
        label = self.syntax or f"{self.name}[{r}, {c}]"

        draw_label(canvas, label, px, py - self.font_size - 8.0, font_size=self.font_size * 1.1, color=DLTheme.YELLOW)

        mat = Matrices(
            values=cast(list[list[Any]], self.values),
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_cells=[(r, c)],
            highlight_color=DLTheme.HIGHLIGHT,
            font_size=self.font_size,
            stroke_color=DLTheme.CYAN,
        )
        mat.draw(canvas, px, py)

        draw_label(
            canvas,
            f"= {format_float(self.values[r][c])}",
            px + cols * (self.cell_size + self.gap) + 16.0,
            py + r * (self.cell_size + self.gap) + (self.cell_size - self.font_size) / 2.0,
            font_size=self.font_size,
            color=DLTheme.GREEN,
        )


@dataclass(slots=True)
class Slicing(Node):
    """Highlight a row/column slice region with syntax (e.g. ``x[1:3, 2:4]``)."""

    values: list[list[float | int]] = field(default_factory=list)
    row_start: int = 0
    row_end: int = 2
    col_start: int = 0
    col_end: int = 2
    name: str = "x"
    syntax: str = ""
    cell_size: float = 40.0
    gap: float = 3.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        rows, cols = _matrix_dims(self.values)
        if rows == 0:
            return

        rs = max(0, min(self.row_start, rows))
        re = max(rs, min(self.row_end, rows))
        cs = max(0, min(self.col_start, cols))
        ce = max(cs, min(self.col_end, cols))

        label = self.syntax or f"{self.name}[{rs}:{re}, {cs}:{ce}]"
        draw_label(canvas, label, px, py - self.font_size - 8.0, font_size=self.font_size * 1.1, color=DLTheme.YELLOW)

        hl = {(r, c) for r in range(rs, re) for c in range(cs, ce)}
        mat = Matrices(
            values=cast(list[list[Any]], self.values),
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_cells=list(hl),
            highlight_color=DLTheme.HIGHLIGHT,
            font_size=self.font_size,
            stroke_color=DLTheme.CYAN,
        )
        mat.draw(canvas, px, py)

        stroke_line = getattr(canvas, "stroke_line", None)
        if stroke_line is not None and hl:
            x0 = px + cs * (self.cell_size + self.gap) - 2.0
            y0 = py + rs * (self.cell_size + self.gap) - 2.0
            x1 = px + ce * (self.cell_size + self.gap) - self.gap + 2.0
            y1 = py + re * (self.cell_size + self.gap) - self.gap + 2.0
            stroke_line(x0, y0, x1, y0, DLTheme.GLOW, 2.0, dash_pattern=(4.0, 3.0))
            stroke_line(x1, y0, x1, y1, DLTheme.GLOW, 2.0, dash_pattern=(4.0, 3.0))
            stroke_line(x1, y1, x0, y1, DLTheme.GLOW, 2.0, dash_pattern=(4.0, 3.0))
            stroke_line(x0, y1, x0, y0, DLTheme.GLOW, 2.0, dash_pattern=(4.0, 3.0))


@dataclass(slots=True)
class Operations(Node):
    """Element-wise binary op between two matrices or vectors with stepped highlight."""

    left: list[list[float | int]] | list[float | int] = field(default_factory=list)
    right: list[list[float | int]] | list[float | int] = field(default_factory=list)
    op: str = "+"
    progress: float = 0.0
    label_left: str = "A"
    label_right: str = "B"
    cell_size: float = 36.0
    gap: float = 3.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        a = _as_matrix(self.left)
        b = _as_matrix(self.right)
        rows, cols = _matrix_dims(a)
        if rows == 0 or _matrix_dims(b) != (rows, cols):
            draw_label(canvas, "shape mismatch", px, py, color=DLTheme.RED)
            return

        result = _elementwise(a, b, self.op)
        total = rows * cols
        active = min(int(self.progress * total), total - 1) if self.progress < 1.0 else -1
        done = self.progress >= 1.0

        hl_a: list[tuple[int, int]] = []
        hl_b: list[tuple[int, int]] = []
        hl_c: list[tuple[int, int]] = []
        if active >= 0:
            ar, ac = divmod(active, cols)
            hl_a.append((ar, ac))
            hl_b.append((ar, ac))
            hl_c.append((ar, ac))
        elif done:
            hl_c = [(r, c) for r in range(rows) for c in range(cols)]

        spacing_y = rows * (self.cell_size + self.gap) + 50.0
        w = cols * (self.cell_size + self.gap)

        draw_label(canvas, self.label_left, px, py - 18.0, font_size=self.font_size, color=DLTheme.BLUE)
        Matrices(
            values=cast(list[list[Any]], a),
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_cells=hl_a,
            highlight_color=DLTheme.HIGHLIGHT,
            stroke_color=DLTheme.BLUE,
            font_size=self.font_size,
        ).draw(canvas, px, py)

        draw_label(
            canvas,
            self.op,
            px + w / 2.0 - 6.0,
            py + spacing_y / 2.0 - 20.0,
            font_size=self.font_size * 1.4,
            color=DLTheme.TEXT,
        )

        draw_label(canvas, self.label_right, px, py + spacing_y - 18.0, font_size=self.font_size, color=DLTheme.PURPLE)
        Matrices(
            values=cast(list[list[Any]], b),
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_cells=hl_b,
            highlight_color=DLTheme.HIGHLIGHT,
            stroke_color=DLTheme.PURPLE,
            font_size=self.font_size,
        ).draw(canvas, px, py + spacing_y)

        draw_arrow(canvas, px + w + 12.0, py + spacing_y / 2.0, px + w + 52.0, py + spacing_y / 2.0, color=DLTheme.TEXT_DIM)

        rx = px + w + 60.0
        draw_label(canvas, "result", rx, py + spacing_y / 2.0 - 50.0, font_size=self.font_size, color=DLTheme.GREEN)
        Matrices(
            values=cast(list[list[Any]], result),
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_cells=hl_c,
            highlight_color=DLTheme.HIGHLIGHT,
            stroke_color=DLTheme.GREEN,
            font_size=self.font_size,
        ).draw(canvas, rx, py + spacing_y / 2.0 - rows * (self.cell_size + self.gap) / 2.0)

        if active >= 0:
            ar, ac = divmod(active, cols)
            eq = f"{format_float(a[ar][ac])} {self.op} {format_float(b[ar][ac])} = {format_float(result[ar][ac])}"
            draw_label(canvas, eq, px, py + 2 * spacing_y + 8.0, font_size=self.font_size, color=DLTheme.YELLOW)


@dataclass(slots=True)
class Broadcasting(Node):
    """Small vector broadcast onto a large matrix; ``progress`` drives expansion."""

    vector: list[float | int] = field(default_factory=list)
    matrix: list[list[float | int]] = field(default_factory=list)
    broadcast_axis: str = "row"
    op: str = "+"
    progress: float = 0.0
    cell_size: float = 34.0
    gap: float = 3.0
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        rows, cols = _matrix_dims(self.matrix)
        if rows == 0 or not self.vector:
            return

        n_vec = len(self.vector)
        p = max(0.0, min(1.0, self.progress))

        draw_label(canvas, "vector", px, py - 18.0, font_size=self.font_size, color=DLTheme.CYAN)
        Vectors(
            values=cast(list[Any], self.vector),
            horizontal=self.broadcast_axis == "col",
            cell_size=self.cell_size,
            gap=self.gap,
            stroke_color=DLTheme.CYAN,
            font_size=self.font_size,
        ).draw(canvas, px, py)

        mat_x = px + (n_vec + 3) * (self.cell_size + self.gap) if self.broadcast_axis == "row" else px
        mat_y = py + (self.cell_size + self.gap) * 3.0 if self.broadcast_axis == "row" else py

        draw_label(canvas, "matrix", mat_x, mat_y - 18.0, font_size=self.font_size, color=DLTheme.BLUE)
        Matrices(
            values=cast(list[list[Any]], self.matrix),
            cell_size=self.cell_size,
            gap=self.gap,
            stroke_color=DLTheme.BLUE,
            font_size=self.font_size,
        ).draw(canvas, mat_x, mat_y)

        ghost_rows = rows if self.broadcast_axis == "row" else 1
        ghost_cols = cols if self.broadcast_axis == "col" else 1
        expanded: list[list[Any]] = []
        for r in range(ghost_rows):
            row: list[Any] = []
            for c in range(ghost_cols):
                if self.broadcast_axis == "row":
                    row.append(self.vector[c % n_vec])
                else:
                    row.append(self.vector[r % n_vec])
            expanded.append(row)

        visible_rows = max(1, int(math.ceil(p * ghost_rows))) if self.broadcast_axis == "row" else ghost_rows
        visible_cols = max(1, int(math.ceil(p * ghost_cols))) if self.broadcast_axis == "col" else ghost_cols

        gx = mat_x
        gy = mat_y + rows * (self.cell_size + self.gap) + 24.0
        draw_label(canvas, f"broadcast {self.op}", gx, gy - 18.0, font_size=self.font_size, color=DLTheme.YELLOW)

        for r in range(visible_rows):
            for c in range(visible_cols):
                cx = gx + c * (self.cell_size + self.gap)
                cy = gy + r * (self.cell_size + self.gap)
                fill = DLTheme.HIGHLIGHT if p > 0.5 else DLTheme.BG_DEEP
                draw_round_cell(
                    canvas,
                    cx,
                    cy,
                    self.cell_size,
                    label=format_float(expanded[r][c]),
                    fill_color=fill,
                    stroke_color=DLTheme.YELLOW,
                    stroke_width=1.5 if p > 0.3 else 1.0,
                    text_color=DLTheme.BG_DEEP if p > 0.5 else DLTheme.TEXT,
                    font_size=self.font_size - 1.0,
                    radius=3.0,
                )
                if p < 1.0 and (r == visible_rows - 1 or c == visible_cols - 1):
                    draw_label(canvas, "…", cx + self.cell_size + 4.0, cy + 4.0, font_size=self.font_size, color=DLTheme.TEXT_DIM)

        if p >= 0.99:
            out = [list(row) for row in self.matrix]
            if self.broadcast_axis == "row":
                for r in range(rows):
                    for c in range(cols):
                        out[r][c] = float(out[r][c]) + float(self.vector[c % n_vec])
            else:
                for r in range(rows):
                    for c in range(cols):
                        out[r][c] = float(out[r][c]) + float(self.vector[r % n_vec])
            draw_label(canvas, "result", gx, gy + visible_rows * (self.cell_size + self.gap) + 30.0, color=DLTheme.GREEN, font_size=self.font_size)
            draw_grid_cells(
                canvas,
                gx,
                gy + visible_rows * (self.cell_size + self.gap) + 44.0,
                min(rows, 4),
                min(cols, 4),
                cell_size=self.cell_size - 4.0,
                gap=self.gap,
                values=out[: min(rows, 4)],
                stroke_color=DLTheme.GREEN,
                font_size=self.font_size - 2.0,
            )


@dataclass(slots=True)
class Vectorization(Node):
    """Compare sequential loop steps (left) vs vectorized parallel grid (right)."""

    values: list[float | int] = field(default_factory=list)
    progress: float = 0.0
    loop_label: str = "for i in range(n):"
    vec_label: str = "x + y  (vectorized)"
    cell_size: float = 32.0
    gap: float = 4.0
    font_size: float = 13.0
    panel_width: float = 200.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        n = len(self.values)
        if n == 0:
            return

        p = max(0.0, min(1.0, self.progress))
        active = min(int(p * n), n - 1) if p < 1.0 else n - 1
        done = p >= 1.0

        left_x = px
        right_x = px + self.panel_width + 40.0

        draw_label(canvas, "Sequential", left_x, py - 6.0, font_size=self.font_size * 1.05, color=DLTheme.RED)
        draw_label(canvas, self.loop_label, left_x, py + 16.0, font_size=self.font_size * 0.95, color=DLTheme.TEXT_DIM)

        code_y = py + 44.0
        stroke_line = getattr(canvas, "stroke_line", None)
        for i in range(n):
            cy = code_y + i * (self.cell_size + self.gap)
            is_active = (i == active) and not done
            is_past = i < active or done
            fill = DLTheme.HIGHLIGHT if is_active else (DLTheme.BG if is_past else DLTheme.BG_DEEP)
            stroke = DLTheme.RED if is_active else (DLTheme.TEXT_DIM if is_past else DLTheme.GRID)
            draw_round_cell(
                canvas,
                left_x,
                cy,
                self.panel_width - 20.0,
                label=f"  step {i}: f(x[{i}]) → {format_float(self.values[i])}",
                fill_color=fill,
                stroke_color=stroke,
                text_color=DLTheme.BG_DEEP if is_active else DLTheme.TEXT,
                font_size=self.font_size - 1.0,
                radius=4.0,
            )
            if is_active and stroke_line is not None:
                stroke_line(left_x - 8.0, cy + self.cell_size / 2.0, left_x - 2.0, cy + self.cell_size / 2.0, DLTheme.RED, 2.5)

        draw_label(canvas, "Vectorized", right_x, py - 6.0, font_size=self.font_size * 1.05, color=DLTheme.GREEN)
        draw_label(canvas, self.vec_label, right_x, py + 16.0, font_size=self.font_size * 0.95, color=DLTheme.TEXT_DIM)

        grid_y = py + 44.0
        hl = {(0, c) for c in range(n)} if done else ({(0, active)} if active >= 0 else set())
        revealed = n if done else max(1, active + 1)
        partial_vals = [self.values[:revealed] + [""] * (n - revealed)]
        draw_grid_cells(
            canvas,
            right_x,
            grid_y,
            1,
            n,
            cell_size=self.cell_size,
            gap=self.gap,
            values=partial_vals,
            highlight=hl,
            fill_color=DLTheme.BG,
            highlight_color=DLTheme.GREEN,
            stroke_color=DLTheme.CYAN,
            font_size=self.font_size,
        )

        mid_y = grid_y + (self.cell_size + self.gap) / 2.0
        draw_arrow(canvas, left_x + self.panel_width, mid_y, right_x - 12.0, mid_y, color=DLTheme.TEXT_DIM)

        speed = "O(n) steps" if not done else "O(1) SIMD batch"
        draw_label(
            canvas,
            speed,
            right_x,
            grid_y + self.cell_size + self.gap + 12.0,
            font_size=self.font_size,
            color=DLTheme.GREEN if done else DLTheme.TEXT_DIM,
        )

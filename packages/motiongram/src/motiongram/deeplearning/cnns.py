"""Visual components for convolutional neural networks in deep learning."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from motiongram.core import Node
from motiongram.canvas import Canvas
from motiongram.deeplearning._draw import (
    DLTheme,
    draw_arrow,
    draw_dot,
    draw_grid_cells,
    draw_label,
    draw_round_cell,
    format_float,
)


def _grid_extent(rows: int, cols: int, cell_size: float, gap: float) -> tuple[float, float]:
    if rows <= 0 or cols <= 0:
        return 0.0, 0.0
    width = cols * cell_size + (cols - 1) * gap
    height = rows * cell_size + (rows - 1) * gap
    return width, height


def _cell_center(
    px: float,
    py: float,
    row: int,
    col: int,
    *,
    cell_size: float,
    gap: float,
) -> tuple[float, float]:
    cx = px + col * (cell_size + gap) + cell_size / 2.0
    cy = py + row * (cell_size + gap) + cell_size / 2.0
    return cx, cy


def _conv2d_valid(
    input_grid: list[list[float]],
    kernel: list[list[float]],
) -> list[list[float]]:
    if not input_grid or not input_grid[0] or not kernel or not kernel[0]:
        return []
    in_rows, in_cols = len(input_grid), len(input_grid[0])
    k_rows, k_cols = len(kernel), len(kernel[0])
    out_rows = in_rows - k_rows + 1
    out_cols = in_cols - k_cols + 1
    if out_rows <= 0 or out_cols <= 0:
        return []
    output: list[list[float]] = [[0.0] * out_cols for _ in range(out_rows)]
    for r in range(out_rows):
        for c in range(out_cols):
            total = 0.0
            for kr in range(k_rows):
                for kc in range(k_cols):
                    total += input_grid[r + kr][c + kc] * kernel[kr][kc]
            output[r][c] = total
    return output


def _heatmap_color(value: float, vmin: float, vmax: float) -> str:
    if vmax <= vmin:
        return DLTheme.BLUE
    t = (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    stops = [
        (0.0, (0x61, 0xaf, 0xef)),
        (0.5, (0xe5, 0xc0, 0x7b)),
        (1.0, (0xe0, 0x6c, 0x75)),
    ]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            r = int(c0[0] + (c1[0] - c0[0]) * u)
            g = int(c0[1] + (c1[1] - c0[1]) * u)
            b = int(c0[2] + (c1[2] - c0[2]) * u)
            return f"#{r:02x}{g:02x}{b:02x}"
    r, g, b = stops[-1][1]
    return f"#{r:02x}{g:02x}{b:02x}"


def _draw_volume_block(
    canvas: Canvas,
    px: float,
    py: float,
    shape: tuple[int, int, int],
    *,
    cell_size: float,
    gap: float,
    depth_offset: tuple[float, float],
    fill_color: str,
    stroke_color: str,
    label: str = "",
    font_size: float = 13.0,
) -> tuple[float, float]:
    """Draw a h x w x c volume as stacked slices; return (width, height)."""
    h, w, c = shape
    if h <= 0 or w <= 0 or c <= 0:
        return 0.0, 0.0

    slice_w, slice_h = _grid_extent(h, w, cell_size, gap)
    dx, dy = depth_offset

    for layer in range(c):
        ox = px + layer * dx
        oy = py + layer * dy
        draw_grid_cells(
            canvas,
            ox,
            oy,
            h,
            w,
            cell_size=cell_size,
            gap=gap,
            fill_color=fill_color,
            stroke_color=stroke_color,
            font_size=max(8.0, font_size * 0.75),
        )
        if layer == c - 1 and label:
            draw_label(canvas, label, ox, oy - font_size - 6.0, font_size=font_size, color=DLTheme.TEXT_DIM)

    total_w = slice_w + abs(dx) * (c - 1)
    total_h = slice_h + abs(dy) * (c - 1)
    return total_w, total_h


@dataclass(slots=True)
class Convolutions(Node):
    """Side-by-side input, kernel, and output grids with sliding-window highlight."""

    input_grid: list[list[float]] = field(default_factory=list)
    kernel: list[list[float]] = field(default_factory=list)
    kernel_row: int = 0
    kernel_col: int = 0
    progress: float = 0.0
    cell_size: float = 26.0
    gap: float = 2.0
    section_gap: float = 36.0
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.input_grid or not self.input_grid[0] or not self.kernel or not self.kernel[0]:
            return

        in_rows, in_cols = len(self.input_grid), len(self.input_grid[0])
        k_rows, k_cols = len(self.kernel), len(self.kernel[0])
        output = _conv2d_valid(self.input_grid, self.kernel)
        if not output:
            return

        out_rows, out_cols = len(output), len(output[0])
        kr = max(0, min(self.kernel_row, out_rows - 1))
        kc = max(0, min(self.kernel_col, out_cols - 1))

        input_hl: set[tuple[int, int]] = set()
        for r in range(k_rows):
            for c in range(k_cols):
                input_hl.add((kr + r, kc + c))

        out_hl = {(kr, kc)}

        in_w, _ = _grid_extent(in_rows, in_cols, self.cell_size, self.gap)
        k_w, _ = _grid_extent(k_rows, k_cols, self.cell_size, self.gap)
        in_x = px
        kernel_x = px + in_w + self.section_gap
        out_x = kernel_x + k_w + self.section_gap

        draw_label(canvas, "Input", in_x, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.BLUE)
        draw_label(canvas, "Kernel", kernel_x, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.PURPLE)
        draw_label(canvas, "Output", out_x, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.GREEN)

        draw_grid_cells(
            canvas,
            in_x,
            py,
            in_rows,
            in_cols,
            cell_size=self.cell_size,
            gap=self.gap,
            values=self.input_grid,
            highlight=input_hl,
            font_size=self.font_size * 0.85,
        )
        draw_grid_cells(
            canvas,
            kernel_x,
            py,
            k_rows,
            k_cols,
            cell_size=self.cell_size,
            gap=self.gap,
            values=self.kernel,
            highlight={(r, c) for r in range(k_rows) for c in range(k_cols)},
            highlight_color=DLTheme.PURPLE,
            font_size=self.font_size * 0.85,
        )
        draw_grid_cells(
            canvas,
            out_x,
            py,
            out_rows,
            out_cols,
            cell_size=self.cell_size,
            gap=self.gap,
            values=output,
            highlight=out_hl,
            highlight_color=DLTheme.GREEN,
            font_size=self.font_size * 0.85,
        )

        stroke_line = getattr(canvas, "stroke_line", None)
        if stroke_line is not None:
            out_cx, out_cy = _cell_center(out_x, py, kr, kc, cell_size=self.cell_size, gap=self.gap)
            k_cells = k_rows * k_cols
            active_lines = int(self.progress * k_cells) if self.progress < 1.0 else k_cells
            idx = 0
            for r in range(k_rows):
                for c in range(k_cols):
                    if idx >= active_lines:
                        break
                    in_cx, in_cy = _cell_center(
                        in_x, py, kr + r, kc + c, cell_size=self.cell_size, gap=self.gap
                    )
                    k_cx, k_cy = _cell_center(
                        kernel_x, py, r, c, cell_size=self.cell_size, gap=self.gap
                    )
                    color = DLTheme.HIGHLIGHT if idx == active_lines - 1 and self.progress < 1.0 else DLTheme.TEXT_DIM
                    width = 2.0 if idx == active_lines - 1 and self.progress < 1.0 else 1.0
                    stroke_line(in_cx, in_cy, out_cx, out_cy, color, width, dash_pattern=(3.0, 3.0))
                    stroke_line(k_cx, k_cy, out_cx, out_cy, color, width, dash_pattern=(3.0, 3.0))
                    idx += 1

        draw_label(
            canvas,
            f"patch ({kr},{kc}) -> {format_float(output[kr][kc])}",
            px,
            py + _grid_extent(in_rows, in_cols, self.cell_size, self.gap)[1] + 14.0,
            font_size=self.font_size,
            color=DLTheme.HIGHLIGHT,
        )


@dataclass(slots=True)
class Channels(Node):
    """RGB or multi-channel grids, stacked or side-by-side with active channel highlight."""

    channels: list[list[list[float]]] = field(default_factory=list)
    channel_idx: int = 0
    layout: str = "stacked"
    cell_size: float = 22.0
    gap: float = 2.0
    depth_offset: tuple[float, float] = (14.0, -14.0)
    side_gap: float = 28.0
    channel_colors: list[str] = field(default_factory=lambda: ["#e06c75", "#98c379", "#61afef"])
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.channels:
            return

        n = len(self.channels)
        active = max(0, min(self.channel_idx, n - 1))
        names = ["R", "G", "B"] if n == 3 else [f"C{i}" for i in range(n)]

        cursor_x = px

        for i, grid in enumerate(self.channels):
            if not grid or not grid[0]:
                continue
            rows, cols = len(grid), len(grid[0])
            is_active = i == active
            stroke = self.channel_colors[i % len(self.channel_colors)] if is_active else DLTheme.GRID
            fill = DLTheme.HIGHLIGHT if is_active else DLTheme.BG
            text_color = DLTheme.BG_DEEP if is_active else DLTheme.TEXT

            if self.layout == "side_by_side":
                gx, gy = cursor_x, py
                cursor_x += _grid_extent(rows, cols, self.cell_size, self.gap)[0] + self.side_gap
            else:
                dx = (n - 1 - i) * self.depth_offset[0]
                dy = (n - 1 - i) * self.depth_offset[1]
                gx = px + dx
                gy = py + dy

            for r in range(rows):
                for c in range(cols):
                    cx = gx + c * (self.cell_size + self.gap)
                    cy = gy + r * (self.cell_size + self.gap)
                    val = grid[r][c]
                    label = format_float(val) if isinstance(val, float) else str(val)
                    draw_round_cell(
                        canvas,
                        cx,
                        cy,
                        self.cell_size,
                        label=label,
                        fill_color=fill,
                        stroke_color=stroke,
                        stroke_width=2.0 if is_active else 1.0,
                        text_color=text_color,
                        font_size=self.font_size * 0.85,
                        radius=3.0,
                    )

            if is_active or self.layout == "side_by_side":
                draw_label(
                    canvas,
                    names[i],
                    gx,
                    gy - self.font_size - 4.0,
                    font_size=self.font_size,
                    color=stroke,
                )

        draw_label(
            canvas,
            f"channel {active}: {names[active]}",
            px,
            py + 120.0,
            font_size=self.font_size,
            color=DLTheme.TEXT,
        )


@dataclass(slots=True)
class ConvolutionalLayers(Node):
    """3D volume blocks showing input and output tensor shapes."""

    input_shape: tuple[int, int, int] = (32, 32, 3)
    output_shape: tuple[int, int, int] = (28, 28, 8)
    cell_size: float = 4.0
    gap: float = 1.0
    depth_offset: tuple[float, float] = (10.0, -10.0)
    block_gap: float = 80.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        in_h, in_w, in_c = self.input_shape
        out_h, out_w, out_c = self.output_shape

        in_label = f"{in_h}x{in_w}x{in_c}"
        out_label = f"{out_h}x{out_w}x{out_c}"

        in_w_px, in_h_px = _draw_volume_block(
            canvas,
            px,
            py,
            self.input_shape,
            cell_size=self.cell_size,
            gap=self.gap,
            depth_offset=self.depth_offset,
            fill_color=DLTheme.BG,
            stroke_color=DLTheme.BLUE,
            label=in_label,
            font_size=self.font_size,
        )

        out_x = px + in_w_px + self.block_gap
        _draw_volume_block(
            canvas,
            out_x,
            py,
            self.output_shape,
            cell_size=self.cell_size,
            gap=self.gap,
            depth_offset=self.depth_offset,
            fill_color=DLTheme.BG,
            stroke_color=DLTheme.GREEN,
            label=out_label,
            font_size=self.font_size,
        )

        arrow_y = py + in_h_px / 2.0
        draw_arrow(
            canvas,
            px + in_w_px + 8.0,
            arrow_y,
            out_x - 8.0,
            arrow_y,
            color=DLTheme.TEXT,
            width=2.0,
        )
        draw_label(
            canvas,
            f"{in_label} -> {out_label}",
            px,
            py + in_h_px + 18.0,
            font_size=self.font_size * 1.05,
            color=DLTheme.HIGHLIGHT,
        )


@dataclass(slots=True)
class FeatureMap(Node):
    """Activation grid colored as a heatmap with max cell highlighted."""

    values: list[list[float]] = field(default_factory=list)
    cell_size: float = 28.0
    gap: float = 2.0
    font_size: float = 11.0
    show_values: bool = True

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.values or not self.values[0]:
            return

        rows, cols = len(self.values), len(self.values[0])
        flat = [self.values[r][c] for r in range(rows) for c in range(cols)]
        vmin, vmax = min(flat), max(flat)
        max_pos = (0, 0)
        max_val = flat[0]
        for r in range(rows):
            for c in range(cols):
                if self.values[r][c] >= max_val:
                    max_val = self.values[r][c]
                    max_pos = (r, c)

        draw_label(canvas, "Feature Map", px, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.TEXT)

        for r in range(rows):
            for c in range(cols):
                val = self.values[r][c]
                cx = px + c * (self.cell_size + self.gap)
                cy = py + r * (self.cell_size + self.gap)
                is_max = (r, c) == max_pos
                fill = DLTheme.HIGHLIGHT if is_max else _heatmap_color(val, vmin, vmax)
                label = format_float(val) if self.show_values else ""
                draw_round_cell(
                    canvas,
                    cx,
                    cy,
                    self.cell_size,
                    label=label,
                    fill_color=fill,
                    stroke_color=DLTheme.YELLOW if is_max else DLTheme.GRID,
                    stroke_width=2.5 if is_max else 1.0,
                    text_color=DLTheme.BG_DEEP if is_max else DLTheme.TEXT,
                    font_size=self.font_size,
                    radius=3.0,
                )
                if is_max:
                    mcx, mcy = cx + self.cell_size / 2.0, cy + self.cell_size / 2.0
                    draw_dot(canvas, mcx, mcy, radius=3.0, color=DLTheme.YELLOW)

        draw_label(
            canvas,
            f"max = {format_float(max_val)} at ({max_pos[0]},{max_pos[1]})",
            px,
            py + _grid_extent(rows, cols, self.cell_size, self.gap)[1] + 12.0,
            font_size=self.font_size,
            color=DLTheme.HIGHLIGHT,
        )


@dataclass(slots=True)
class ReceptiveField(Node):
    """Input grid with bounding box showing receptive region for an output cell."""

    input_grid: list[list[float]] = field(default_factory=list)
    output_row: int = 0
    output_col: int = 0
    receptive_h: int = 3
    receptive_w: int = 3
    cell_size: float = 26.0
    gap: float = 2.0
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.input_grid or not self.input_grid[0]:
            return

        rows, cols = len(self.input_grid), len(self.input_grid[0])
        out_rows = max(1, rows - self.receptive_h + 1)
        out_cols = max(1, cols - self.receptive_w + 1)
        orow = max(0, min(self.output_row, out_rows - 1))
        ocol = max(0, min(self.output_col, out_cols - 1))

        rf_cells: set[tuple[int, int]] = set()
        for r in range(self.receptive_h):
            for c in range(self.receptive_w):
                if orow + r < rows and ocol + c < cols:
                    rf_cells.add((orow + r, ocol + c))

        draw_label(canvas, "Input", px, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.BLUE)
        draw_grid_cells(
            canvas,
            px,
            py,
            rows,
            cols,
            cell_size=self.cell_size,
            gap=self.gap,
            values=self.input_grid,
            highlight=rf_cells,
            font_size=self.font_size * 0.85,
        )

        stroke_line = getattr(canvas, "stroke_line", None)
        if stroke_line is not None and rf_cells:
            min_r = min(r for r, _ in rf_cells)
            max_r = max(r for r, _ in rf_cells)
            min_c = min(c for _, c in rf_cells)
            max_c = max(c for _, c in rf_cells)
            x0 = px + min_c * (self.cell_size + self.gap) - 2.0
            y0 = py + min_r * (self.cell_size + self.gap) - 2.0
            x1 = px + (max_c + 1) * (self.cell_size + self.gap) - self.gap + 2.0
            y1 = py + (max_r + 1) * (self.cell_size + self.gap) - self.gap + 2.0
            stroke_line(x0, y0, x1, y0, DLTheme.YELLOW, 2.5, dash_pattern=(5.0, 3.0))
            stroke_line(x1, y0, x1, y1, DLTheme.YELLOW, 2.5, dash_pattern=(5.0, 3.0))
            stroke_line(x1, y1, x0, y1, DLTheme.YELLOW, 2.5, dash_pattern=(5.0, 3.0))
            stroke_line(x0, y1, x0, y0, DLTheme.YELLOW, 2.5, dash_pattern=(5.0, 3.0))

        out_x = px + _grid_extent(rows, cols, self.cell_size, self.gap)[0] + 40.0
        out_y = py + orow * (self.cell_size + self.gap)
        draw_label(canvas, "Output cell", out_x, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.GREEN)
        draw_round_cell(
            canvas,
            out_x,
            out_y,
            self.cell_size,
            label=f"({orow},{ocol})",
            fill_color=DLTheme.GREEN,
            stroke_color=DLTheme.GREEN,
            text_color=DLTheme.BG_DEEP,
            font_size=self.font_size * 0.85,
        )
        draw_arrow(
            canvas,
            px + (ocol + self.receptive_w / 2.0) * (self.cell_size + self.gap),
            py + (orow + self.receptive_h / 2.0) * (self.cell_size + self.gap),
            out_x,
            out_y + self.cell_size / 2.0,
            color=DLTheme.TEXT_DIM,
        )


@dataclass(slots=True)
class Padding(Node):
    """Core input surrounded by dashed zero-padding border."""

    core_input: list[list[float]] = field(default_factory=list)
    pad_size: int = 1
    cell_size: float = 26.0
    gap: float = 2.0
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.core_input or not self.core_input[0]:
            return

        core_rows, core_cols = len(self.core_input), len(self.core_input[0])
        p = max(0, self.pad_size)
        total_rows = core_rows + 2 * p
        total_cols = core_cols + 2 * p

        padded: list[list[float | str]] = [[0.0] * total_cols for _ in range(total_rows)]
        for r in range(core_rows):
            for c in range(core_cols):
                padded[p + r][p + c] = self.core_input[r][c]

        draw_label(canvas, "Padded Input", px, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.TEXT)

        for r in range(total_rows):
            for c in range(total_cols):
                cx = px + c * (self.cell_size + self.gap)
                cy = py + r * (self.cell_size + self.gap)
                is_pad = r < p or c < p or r >= p + core_rows or c >= p + core_cols
                val = padded[r][c]
                label = "0" if is_pad else (format_float(val) if isinstance(val, float) else str(val))
                draw_round_cell(
                    canvas,
                    cx,
                    cy,
                    self.cell_size,
                    label=label,
                    fill_color=DLTheme.BG_DEEP if is_pad else DLTheme.BG,
                    stroke_color=DLTheme.TEXT_DIM if is_pad else DLTheme.CYAN,
                    stroke_width=1.0 if is_pad else 1.5,
                    text_color=DLTheme.TEXT_DIM if is_pad else DLTheme.TEXT,
                    font_size=self.font_size * 0.85,
                    radius=3.0,
                )

        stroke_line = getattr(canvas, "stroke_line", None)
        if stroke_line is not None and p > 0:
            x0 = px + p * (self.cell_size + self.gap) - 3.0
            y0 = py + p * (self.cell_size + self.gap) - 3.0
            x1 = px + (p + core_cols) * (self.cell_size + self.gap) - self.gap + 3.0
            y1 = py + (p + core_rows) * (self.cell_size + self.gap) - self.gap + 3.0
            stroke_line(x0, y0, x1, y0, DLTheme.HIGHLIGHT, 2.0, dash_pattern=(4.0, 4.0))
            stroke_line(x1, y0, x1, y1, DLTheme.HIGHLIGHT, 2.0, dash_pattern=(4.0, 4.0))
            stroke_line(x1, y1, x0, y1, DLTheme.HIGHLIGHT, 2.0, dash_pattern=(4.0, 4.0))
            stroke_line(x0, y1, x0, y0, DLTheme.HIGHLIGHT, 2.0, dash_pattern=(4.0, 4.0))

        draw_label(
            canvas,
            f"pad = {p}",
            px,
            py + _grid_extent(total_rows, total_cols, self.cell_size, self.gap)[1] + 12.0,
            font_size=self.font_size,
            color=DLTheme.TEXT_DIM,
        )


@dataclass(slots=True)
class Stride(Node):
    """Input grid showing kernel positions at stride intervals."""

    input_grid: list[list[float]] = field(default_factory=list)
    kernel_size: int = 3
    stride_val: int = 2
    active_row: int = 0
    active_col: int = 0
    cell_size: float = 26.0
    gap: float = 2.0
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.input_grid or not self.input_grid[0]:
            return

        rows, cols = len(self.input_grid), len(self.input_grid[0])
        k = max(1, self.kernel_size)
        s = max(1, self.stride_val)

        positions: list[tuple[int, int]] = []
        for r in range(0, rows - k + 1, s):
            for c in range(0, cols - k + 1, s):
                positions.append((r, c))

        if not positions:
            return

        arow, acol = self.active_row, self.active_col
        if (arow, acol) not in positions:
            idx = max(0, min(int(self.active_row), len(positions) - 1))
            arow, acol = positions[idx]

        active_patch: set[tuple[int, int]] = set()
        for r in range(k):
            for c in range(k):
                active_patch.add((arow + r, acol + c))

        draw_label(canvas, "Input", px, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.BLUE)
        draw_grid_cells(
            canvas,
            px,
            py,
            rows,
            cols,
            cell_size=self.cell_size,
            gap=self.gap,
            values=self.input_grid,
            highlight=active_patch,
            font_size=self.font_size * 0.85,
        )

        stroke_line = getattr(canvas, "stroke_line", None)
        if stroke_line is not None:
            for pr, pc in positions:
                if (pr, pc) == (arow, acol):
                    continue
                x0 = px + pc * (self.cell_size + self.gap) - 1.0
                y0 = py + pr * (self.cell_size + self.gap) - 1.0
                x1 = px + (pc + k) * (self.cell_size + self.gap) - self.gap + 1.0
                y1 = py + (pr + k) * (self.cell_size + self.gap) - self.gap + 1.0
                stroke_line(x0, y0, x1, y0, DLTheme.TEXT_DIM, 1.0, dash_pattern=(3.0, 3.0))
                stroke_line(x1, y0, x1, y1, DLTheme.TEXT_DIM, 1.0, dash_pattern=(3.0, 3.0))
                stroke_line(x1, y1, x0, y1, DLTheme.TEXT_DIM, 1.0, dash_pattern=(3.0, 3.0))
                stroke_line(x0, y1, x0, y0, DLTheme.TEXT_DIM, 1.0, dash_pattern=(3.0, 3.0))

            x0 = px + acol * (self.cell_size + self.gap) - 2.0
            y0 = py + arow * (self.cell_size + self.gap) - 2.0
            x1 = px + (acol + k) * (self.cell_size + self.gap) - self.gap + 2.0
            y1 = py + (arow + k) * (self.cell_size + self.gap) - self.gap + 2.0
            stroke_line(x0, y0, x1, y0, DLTheme.HIGHLIGHT, 2.5)
            stroke_line(x1, y0, x1, y1, DLTheme.HIGHLIGHT, 2.5)
            stroke_line(x1, y1, x0, y1, DLTheme.HIGHLIGHT, 2.5)
            stroke_line(x0, y1, x0, y0, DLTheme.HIGHLIGHT, 2.5)

        draw_label(
            canvas,
            f"stride = {s}, kernel = {k}x{k}, pos ({arow},{acol})",
            px,
            py + _grid_extent(rows, cols, self.cell_size, self.gap)[1] + 12.0,
            font_size=self.font_size,
            color=DLTheme.HIGHLIGHT,
        )


@dataclass(slots=True)
class Pooling(Node):
    """Max or average pooling over a window with highlighted quadrant and output value."""

    input_grid: list[list[float]] = field(default_factory=list)
    pool_size: int = 2
    pool_row: int = 0
    pool_col: int = 0
    pool_type: str = "max"
    cell_size: float = 28.0
    gap: float = 2.0
    font_size: float = 12.0

    def _pool_value(self, cells: list[float]) -> float:
        if not cells:
            return 0.0
        if self.pool_type.lower() == "avg":
            return sum(cells) / len(cells)
        return max(cells)

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.input_grid or not self.input_grid[0]:
            return

        rows, cols = len(self.input_grid), len(self.input_grid[0])
        ps = max(1, self.pool_size)
        out_rows = math.ceil(rows / ps)
        out_cols = math.ceil(cols / ps)

        prow = max(0, min(self.pool_row, out_rows - 1))
        pcol = max(0, min(self.pool_col, out_cols - 1))

        r0, c0 = prow * ps, pcol * ps
        window: set[tuple[int, int]] = set()
        cells: list[float] = []
        for r in range(r0, min(r0 + ps, rows)):
            for c in range(c0, min(c0 + ps, cols)):
                window.add((r, c))
                cells.append(float(self.input_grid[r][c]))

        pooled = self._pool_value(cells)
        op_name = "max" if self.pool_type.lower() != "avg" else "avg"

        draw_label(canvas, "Input", px, py - self.font_size - 8.0, font_size=self.font_size, color=DLTheme.BLUE)
        draw_grid_cells(
            canvas,
            px,
            py,
            rows,
            cols,
            cell_size=self.cell_size,
            gap=self.gap,
            values=self.input_grid,
            highlight=window,
            font_size=self.font_size * 0.85,
        )

        out_x = px + _grid_extent(rows, cols, self.cell_size, self.gap)[0] + 40.0
        out_y = py + prow * (self.cell_size + self.gap)
        draw_label(
            canvas,
            f"{op_name} pool {ps}x{ps}",
            out_x,
            py - self.font_size - 8.0,
            font_size=self.font_size,
            color=DLTheme.GREEN,
        )
        draw_round_cell(
            canvas,
            out_x,
            out_y,
            self.cell_size,
            label=format_float(pooled),
            fill_color=DLTheme.GREEN,
            stroke_color=DLTheme.GREEN,
            text_color=DLTheme.BG_DEEP,
            font_size=self.font_size,
        )

        draw_arrow(
            canvas,
            px + (c0 + ps / 2.0) * (self.cell_size + self.gap),
            py + (r0 + ps / 2.0) * (self.cell_size + self.gap),
            out_x,
            out_y + self.cell_size / 2.0,
            color=DLTheme.HIGHLIGHT,
            width=2.0,
        )


@dataclass(slots=True)
class ModernCNN(Node):
    """Flowchart: Conv -> ReLU -> Pool with residual skip connection."""

    box_width: float = 90.0
    box_height: float = 44.0
    box_gap: float = 36.0
    skip_height: float = 70.0
    font_size: float = 14.0
    active_stage: int | None = None

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stages = [
            ("Conv", DLTheme.BLUE),
            ("ReLU", DLTheme.YELLOW),
            ("Pool", DLTheme.GREEN),
        ]

        centers: list[tuple[float, float]] = []
        for i, (name, color) in enumerate(stages):
            bx = px + i * (self.box_width + self.box_gap)
            by = py
            is_active = self.active_stage == i
            fill = DLTheme.BG if not is_active else color
            text_col = DLTheme.TEXT if not is_active else DLTheme.BG_DEEP
            stroke_w = 2.5 if is_active else 1.5
            fill_round_rect = getattr(canvas, "fill_round_rect", None)
            if fill_round_rect is not None:
                fill_round_rect(
                    bx,
                    by,
                    bx + self.box_width,
                    by + self.box_height,
                    8.0,
                    fill_color=fill,
                    stroke_color=color if stroke_w > 0 else None,
                    stroke_width=stroke_w,
                )
            draw_label(
                canvas,
                name,
                bx + (self.box_width - len(name) * self.font_size * 0.55) / 2.0,
                by + (self.box_height - self.font_size) / 2.0,
                font_size=self.font_size,
                color=text_col,
            )
            cx = bx + self.box_width / 2.0
            cy = by + self.box_height / 2.0
            centers.append((cx, cy))

        for i in range(len(centers) - 1):
            x0 = centers[i][0] + self.box_width / 2.0
            x1 = centers[i + 1][0] - self.box_width / 2.0
            y = centers[i][1]
            draw_arrow(canvas, x0, y, x1, y, color=DLTheme.TEXT_DIM, width=2.0)

        if len(centers) >= 2:
            x_start = centers[0][0]
            x_end = centers[-1][0]
            y_top = py - self.skip_height
            stroke_line = getattr(canvas, "stroke_line", None)
            if stroke_line is not None:
                stroke_line(x_start, y_top, x_end, y_top, DLTheme.PURPLE, 2.0, dash_pattern=(6.0, 4.0))
                stroke_line(x_start, py, x_start, y_top, DLTheme.PURPLE, 2.0, dash_pattern=(6.0, 4.0))
                stroke_line(x_end, y_top, x_end, py, DLTheme.PURPLE, 2.0, dash_pattern=(6.0, 4.0))
            draw_label(canvas, "skip", x_end - 30.0, y_top - 18.0, font_size=self.font_size * 0.9, color=DLTheme.PURPLE)
            draw_arrow(canvas, x_end - 20.0, y_top, x_end, py, color=DLTheme.PURPLE, width=2.0)

        draw_label(
            canvas,
            "Modern CNN block",
            px,
            py + self.box_height + 20.0,
            font_size=self.font_size,
            color=DLTheme.TEXT,
        )

"""Visual components for multilayer perceptrons and training concepts."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

from motiongram.core import Node
from motiongram.canvas import Canvas
from motiongram.deeplearning._draw import (
    DLTheme,
    draw_arrow,
    draw_dot,
    draw_label,
    draw_plot_border,
    draw_polyline,
    draw_round_cell,
    format_float,
)


def _activation_value(name: str, x: float) -> float:
    n = name.lower()
    if n == "relu":
        return max(0.0, x)
    if n == "sigmoid":
        if x >= 0.0:
            z = math.exp(-x)
            return 1.0 / (1.0 + z)
        z = math.exp(x)
        return z / (1.0 + z)
    if n == "tanh":
        return math.tanh(x)
    if n == "gelu":
        return 0.5 * x * (1.0 + math.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x**3)))
    return max(0.0, x)


def _neuron_positions(
    layer_sizes: list[int],
    px: float,
    py: float,
    *,
    layer_spacing: float,
    node_spacing: float,
) -> list[list[tuple[float, float]]]:
    """Return per-layer lists of (x, y) centers."""
    if not layer_sizes:
        return []
    max_n = max(layer_sizes)
    span = max(0, max_n - 1) * node_spacing
    layers: list[list[tuple[float, float]]] = []
    for li, count in enumerate(layer_sizes):
        lx = px + li * layer_spacing
        layer_h = max(0, count - 1) * node_spacing
        y0 = py + (span - layer_h) / 2.0
        pts = [(lx, y0 + i * node_spacing) for i in range(count)]
        layers.append(pts)
    return layers


def _edge_pulse_color(
    layer_idx: int,
    num_layers: int,
    progress: float,
    *,
    forward: bool,
    active_color: str,
    dim_color: str,
) -> str:
    """Highlight edges between layer_idx and layer_idx+1 based on progress."""
    if num_layers < 2:
        return dim_color
    seg = 1.0 / (num_layers - 1)
    if forward:
        center = layer_idx * seg
    else:
        center = (num_layers - 2 - layer_idx) * seg
    dist = abs(progress - center)
    if dist < seg * 0.45:
        return active_color
    return dim_color


def _draw_neuron(
    canvas: Canvas,
    x: float,
    y: float,
    radius: float,
    *,
    fill: str,
    stroke: str,
    stroke_width: float = 2.0,
) -> None:
    fill_ellipse = getattr(canvas, "fill_ellipse", None)
    if fill_ellipse is not None:
        fill_ellipse(
            x,
            y,
            radius,
            radius,
            fill_color=fill,
            stroke_color=stroke,
            stroke_width=stroke_width,
        )


def _draw_cross(canvas: Canvas, x: float, y: float, size: float, color: str) -> None:
    stroke_line = getattr(canvas, "stroke_line", None)
    if stroke_line is None:
        return
    h = size * 0.55
    stroke_line(x - h, y - h, x + h, y + h, color, 2.0)
    stroke_line(x - h, y + h, x + h, y - h, color, 2.0)


def _draw_inter_layer_edges(
    canvas: Canvas,
    positions: list[list[tuple[float, float]]],
    *,
    node_radius: float,
    n_layers: int,
    progress: float,
    forward: bool,
    pulse_color: str,
    dim_color: str,
) -> None:
    stroke_line = getattr(canvas, "stroke_line", None)
    if stroke_line is None:
        return
    for li in range(n_layers - 1):
        edge_color = _edge_pulse_color(
            li,
            n_layers,
            progress,
            forward=forward,
            active_color=pulse_color,
            dim_color=dim_color,
        )
        w = 2.5 if edge_color == pulse_color else 1.0
        for x0, y0 in positions[li]:
            for x1, y1 in positions[li + 1]:
                stroke_line(
                    x0 + node_radius,
                    y0,
                    x1 - node_radius,
                    y1,
                    edge_color,
                    w,
                )


@dataclass(slots=True)
class HiddenLayers(Node):
    """Neural network graph with optional weight lines and forward pulse across layers."""

    layer_sizes: list[int] = field(default_factory=lambda: [3, 4, 4, 2])
    node_radius: float = 18.0
    layer_spacing: float = 120.0
    node_spacing: float = 50.0
    progress: float = 0.0
    show_weights: bool = True
    weight_color: str = DLTheme.GRID
    active_color: str = DLTheme.BLUE
    neuron_fill: str = DLTheme.BG_DEEP
    neuron_stroke: str = DLTheme.CYAN
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.layer_sizes:
            return

        positions = _neuron_positions(
            self.layer_sizes,
            px,
            py,
            layer_spacing=self.layer_spacing,
            node_spacing=self.node_spacing,
        )
        n_layers = len(self.layer_sizes)
        active_layer = (
            min(int(self.progress * n_layers), n_layers - 1)
            if self.progress < 1.0
            else n_layers - 1
        )

        if self.show_weights:
            _draw_inter_layer_edges(
                canvas,
                positions,
                node_radius=self.node_radius,
                n_layers=n_layers,
                progress=self.progress,
                forward=True,
                pulse_color=self.active_color,
                dim_color=self.weight_color,
            )

        for li, pts in enumerate(positions):
            is_active = li == active_layer
            fill = self.active_color if is_active else self.neuron_fill
            stroke = self.active_color if is_active else self.neuron_stroke
            for nx, ny in pts:
                _draw_neuron(
                    canvas,
                    nx,
                    ny,
                    self.node_radius,
                    fill=fill,
                    stroke=stroke,
                    stroke_width=2.5 if is_active else 1.5,
                )

        draw_label(
            canvas,
            "hidden layers",
            px,
            py - self.node_radius - 22.0,
            font_size=self.font_size,
            color=DLTheme.TEXT_DIM,
        )


@dataclass(slots=True)
class ActivationFunctions(Node):
    """Plot an activation curve with a cursor at ``input_val``."""

    activation: str = "relu"
    input_val: float = 0.0
    width: float = 280.0
    height: float = 180.0
    x_min: float = -2.0
    x_max: float = 3.0
    curve_color: str = DLTheme.BLUE
    cursor_color: str = DLTheme.YELLOW
    grid_color: str = DLTheme.GRID
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        draw_plot_border(canvas, px, py, self.width, self.height, color=self.grid_color)

        y_min, y_max = -1.2, 1.2
        act = self.activation.lower()
        if act == "relu":
            y_min, y_max = -0.2, 3.2
        elif act == "sigmoid":
            y_min, y_max = -0.1, 1.1

        def to_screen(xv: float, yv: float) -> tuple[float, float]:
            tx = (xv - self.x_min) / (self.x_max - self.x_min)
            ty = (yv - y_min) / (y_max - y_min) if y_max != y_min else 0.5
            return px + tx * self.width, py + self.height - ty * self.height

        samples = 80
        points: list[tuple[float, float]] = []
        for i in range(samples + 1):
            t = i / samples
            xv = self.x_min + t * (self.x_max - self.x_min)
            yv = _activation_value(self.activation, xv)
            points.append(to_screen(xv, yv))

        draw_polyline(canvas, points, color=self.curve_color, width=2.5)

        iv = max(self.x_min, min(self.x_max, self.input_val))
        out = _activation_value(self.activation, iv)
        cx, _ = to_screen(iv, 0.0)
        _, curve_y = to_screen(iv, out)

        if stroke_line is not None:
            stroke_line(
                cx,
                py + self.height,
                cx,
                py,
                self.cursor_color,
                1.5,
                dash_pattern=(4.0, 4.0),
            )

        draw_dot(canvas, cx, curve_y, radius=5.0, color=self.cursor_color)

        draw_label(
            canvas,
            f"{self.activation}({format_float(iv, precision=2)}) = {format_float(out, precision=2)}",
            px,
            py + self.height + 8.0,
            font_size=self.font_size,
            color=DLTheme.TEXT,
        )


@dataclass(slots=True)
class ForwardProp(Node):
    """Neural network with left-to-right green pulse on inter-layer edges."""

    layer_sizes: list[int] = field(default_factory=lambda: [3, 4, 4, 2])
    node_radius: float = 18.0
    layer_spacing: float = 120.0
    node_spacing: float = 50.0
    progress: float = 0.0
    pulse_color: str = DLTheme.GREEN
    weight_color: str = DLTheme.GRID
    neuron_fill: str = DLTheme.BG_DEEP
    neuron_stroke: str = DLTheme.CYAN
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.layer_sizes:
            return

        positions = _neuron_positions(
            self.layer_sizes,
            px,
            py,
            layer_spacing=self.layer_spacing,
            node_spacing=self.node_spacing,
        )
        n_layers = len(self.layer_sizes)

        _draw_inter_layer_edges(
            canvas,
            positions,
            node_radius=self.node_radius,
            n_layers=n_layers,
            progress=self.progress,
            forward=True,
            pulse_color=self.pulse_color,
            dim_color=self.weight_color,
        )

        active_layer = min(int(self.progress * n_layers), n_layers - 1)
        for li, pts in enumerate(positions):
            lit = li <= active_layer
            fill = self.pulse_color if lit else self.neuron_fill
            stroke = self.pulse_color if lit else self.neuron_stroke
            for nx, ny in pts:
                _draw_neuron(canvas, nx, ny, self.node_radius, fill=fill, stroke=stroke)

        draw_label(
            canvas,
            "forward pass",
            px,
            py - self.node_radius - 22.0,
            font_size=self.font_size,
            color=self.pulse_color,
        )


@dataclass(slots=True)
class BackwardProp(Node):
    """Neural network with right-to-left red/orange pulse on inter-layer edges."""

    layer_sizes: list[int] = field(default_factory=lambda: [3, 4, 4, 2])
    node_radius: float = 18.0
    layer_spacing: float = 120.0
    node_spacing: float = 50.0
    progress: float = 0.0
    pulse_color: str = DLTheme.RED
    weight_color: str = DLTheme.GRID
    neuron_fill: str = DLTheme.BG_DEEP
    neuron_stroke: str = DLTheme.CYAN
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.layer_sizes:
            return

        positions = _neuron_positions(
            self.layer_sizes,
            px,
            py,
            layer_spacing=self.layer_spacing,
            node_spacing=self.node_spacing,
        )
        n_layers = len(self.layer_sizes)
        rev_progress = 1.0 - max(0.0, min(1.0, self.progress))

        _draw_inter_layer_edges(
            canvas,
            positions,
            node_radius=self.node_radius,
            n_layers=n_layers,
            progress=rev_progress,
            forward=False,
            pulse_color=self.pulse_color,
            dim_color=self.weight_color,
        )

        active_from_right = min(int(self.progress * n_layers), n_layers - 1)
        for li, pts in enumerate(positions):
            lit = li >= n_layers - 1 - active_from_right
            fill = self.pulse_color if lit else self.neuron_fill
            stroke = self.pulse_color if lit else self.neuron_stroke
            for nx, ny in pts:
                _draw_neuron(canvas, nx, ny, self.node_radius, fill=fill, stroke=stroke)

        draw_label(
            canvas,
            "backward pass",
            px,
            py - self.node_radius - 22.0,
            font_size=self.font_size,
            color=self.pulse_color,
        )


@dataclass(slots=True)
class ComputationalGraphs(Node):
    """Boxes for ops with forward values on top and gradients below."""

    nodes: list[tuple[str, float, float]] = field(
        default_factory=lambda: [
            ("x", 1.2, 0.0),
            ("*", 2.4, 1.0),
            ("+", 3.1, 0.5),
            ("loss", 0.8, 1.0),
        ],
    )
    box_width: float = 72.0
    box_height: float = 56.0
    h_spacing: float = 100.0
    fill_color: str = DLTheme.BG
    stroke_color: str = DLTheme.PURPLE
    forward_color: str = DLTheme.CYAN
    grad_color: str = DLTheme.GREEN
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        if not self.nodes:
            return

        centers: list[tuple[float, float]] = []
        for i, _ in enumerate(self.nodes):
            cx = px + i * (self.box_width + self.h_spacing) + self.box_width / 2.0
            cy = py + self.box_height / 2.0
            centers.append((cx, cy))

        for i in range(len(centers) - 1):
            draw_arrow(
                canvas,
                centers[i][0] + self.box_width / 2.0,
                centers[i][1],
                centers[i + 1][0] - self.box_width / 2.0,
                centers[i + 1][1],
                color=DLTheme.TEXT_DIM,
                width=1.5,
            )

        for i, (name, fwd, grad) in enumerate(self.nodes):
            bx = px + i * (self.box_width + self.h_spacing)
            if fill_round_rect is not None:
                fill_round_rect(
                    bx,
                    py,
                    bx + self.box_width,
                    py + self.box_height,
                    6.0,
                    fill_color=self.fill_color,
                    stroke_color=self.stroke_color,
                    stroke_width=1.5,
                )
            draw_label(
                canvas,
                name,
                bx + 8.0,
                py + 6.0,
                font_size=self.font_size * 1.1,
                color=DLTheme.TEXT,
            )
            draw_label(
                canvas,
                format_float(fwd, precision=2),
                bx + 8.0,
                py + self.box_height * 0.38,
                font_size=self.font_size,
                color=self.forward_color,
            )
            draw_label(
                canvas,
                f"d {format_float(grad, precision=2)}",
                bx + 8.0,
                py + self.box_height - self.font_size - 10.0,
                font_size=self.font_size * 0.95,
                color=self.grad_color,
            )


@dataclass(slots=True)
class VanishingGradients(Node):
    """Bar chart of gradient magnitudes decaying per layer."""

    layer_count: int = 6
    decay: float = 0.35
    progress: float = 0.0
    bar_width: float = 36.0
    bar_gap: float = 14.0
    max_height: float = 140.0
    chart_width: float = 320.0
    chart_height: float = 160.0
    bar_color: str = DLTheme.PURPLE
    dim_color: str = DLTheme.GRID
    font_size: float = 12.0

    def _magnitudes(self) -> list[float]:
        return [self.decay**i for i in range(self.layer_count)]

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        mags = self._magnitudes()
        if not mags:
            return

        draw_plot_border(canvas, px, py, self.chart_width, self.chart_height)
        max_mag = max(mags) or 1.0
        total_bars_w = self.layer_count * self.bar_width + (self.layer_count - 1) * self.bar_gap
        x0 = px + (self.chart_width - total_bars_w) / 2.0
        baseline = py + self.chart_height - 8.0
        reveal = max(0.0, min(1.0, self.progress)) * self.layer_count

        for i, mag in enumerate(mags):
            bx = x0 + i * (self.bar_width + self.bar_gap)
            target_h = (mag / max_mag) * self.max_height
            frac = max(0.0, min(1.0, reveal - i))
            h = target_h * frac
            color = self.bar_color if frac > 0.01 else self.dim_color
            if fill_round_rect is not None and h > 0.5:
                fill_round_rect(
                    bx,
                    baseline - h,
                    bx + self.bar_width,
                    baseline,
                    4.0,
                    fill_color=color,
                    stroke_color=None,
                    stroke_width=0.0,
                )
            draw_label(
                canvas,
                f"L{i + 1}",
                bx + 4.0,
                baseline + 4.0,
                font_size=self.font_size * 0.9,
                color=DLTheme.TEXT_DIM,
            )
            if frac >= 1.0:
                draw_label(
                    canvas,
                    format_float(mag, precision=3),
                    bx,
                    baseline - h - 16.0,
                    font_size=self.font_size * 0.85,
                    color=DLTheme.TEXT,
                )

        if stroke_line is not None:
            stroke_line(px, baseline, px + self.chart_width, baseline, DLTheme.GRID, 1.0)

        draw_label(
            canvas,
            "vanishing gradients",
            px,
            py - 18.0,
            font_size=self.font_size,
            color=DLTheme.TEXT_DIM,
        )


@dataclass(slots=True)
class ExplodingGradients(Node):
    """Bar chart of gradient magnitudes growing per layer."""

    layer_count: int = 6
    growth: float = 1.55
    progress: float = 0.0
    bar_width: float = 36.0
    bar_gap: float = 14.0
    max_height: float = 140.0
    chart_width: float = 320.0
    chart_height: float = 160.0
    bar_color: str = DLTheme.RED
    dim_color: str = DLTheme.GRID
    font_size: float = 12.0

    def _magnitudes(self) -> list[float]:
        return [self.growth**i for i in range(self.layer_count)]

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        mags = self._magnitudes()
        if not mags:
            return

        draw_plot_border(canvas, px, py, self.chart_width, self.chart_height)
        max_mag = max(mags) or 1.0
        total_bars_w = self.layer_count * self.bar_width + (self.layer_count - 1) * self.bar_gap
        x0 = px + (self.chart_width - total_bars_w) / 2.0
        baseline = py + self.chart_height - 8.0
        reveal = max(0.0, min(1.0, self.progress)) * self.layer_count

        for i, mag in enumerate(mags):
            bx = x0 + i * (self.bar_width + self.bar_gap)
            target_h = (mag / max_mag) * self.max_height
            frac = max(0.0, min(1.0, reveal - i))
            h = target_h * frac
            color = self.bar_color if frac > 0.01 else self.dim_color
            if fill_round_rect is not None and h > 0.5:
                fill_round_rect(
                    bx,
                    baseline - h,
                    bx + self.bar_width,
                    baseline,
                    4.0,
                    fill_color=color,
                    stroke_color=None,
                    stroke_width=0.0,
                )
            draw_label(
                canvas,
                f"L{i + 1}",
                bx + 4.0,
                baseline + 4.0,
                font_size=self.font_size * 0.9,
                color=DLTheme.TEXT_DIM,
            )
            if frac >= 1.0:
                draw_label(
                    canvas,
                    format_float(mag, precision=2),
                    bx,
                    baseline - h - 16.0,
                    font_size=self.font_size * 0.85,
                    color=DLTheme.TEXT,
                )

        if stroke_line is not None:
            stroke_line(px, baseline, px + self.chart_width, baseline, DLTheme.GRID, 1.0)

        draw_label(
            canvas,
            "exploding gradients",
            px,
            py - 18.0,
            font_size=self.font_size,
            color=DLTheme.TEXT_DIM,
        )


@dataclass(slots=True)
class ParamInit(Node):
    """Histogram of weight draws plus a small weight-matrix preview."""

    init_type: str = "normal"
    seed: int = 42
    num_samples: int = 200
    num_bins: int = 12
    matrix_rows: int = 4
    matrix_cols: int = 4
    progress: float = 1.0
    hist_width: float = 200.0
    hist_height: float = 120.0
    cell_size: float = 28.0
    gap: float = 3.0
    bar_color: str = DLTheme.BLUE
    matrix_color: str = DLTheme.CYAN
    font_size: float = 12.0

    def _sample_weights(self) -> list[float]:
        rng = random.Random(self.seed)
        n = self.matrix_rows * self.matrix_cols
        count = max(n, self.num_samples)
        if self.init_type.lower() == "uniform":
            return [rng.uniform(-1.0, 1.0) for _ in range(count)]
        return [rng.gauss(0.0, 0.5) for _ in range(count)]

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        samples = self._sample_weights()
        prog = max(0.0, min(1.0, self.progress))

        counts = [0] * self.num_bins
        lo, hi = min(samples), max(samples)
        span = hi - lo if hi > lo else 1.0
        for s in samples:
            idx = min(self.num_bins - 1, int((s - lo) / span * self.num_bins))
            counts[idx] += 1
        max_count = max(counts) or 1
        bar_w = self.hist_width / self.num_bins

        for i, c in enumerate(counts):
            bx = px + i * bar_w + 2.0
            target_h = (c / max_count) * self.hist_height
            h = target_h * prog
            if fill_round_rect is not None and h > 0.5:
                fill_round_rect(
                    bx,
                    py + self.hist_height - h,
                    bx + bar_w - 4.0,
                    py + self.hist_height,
                    3.0,
                    fill_color=self.bar_color,
                    stroke_color=None,
                    stroke_width=0.0,
                )

        draw_plot_border(canvas, px, py, self.hist_width, self.hist_height)
        draw_label(
            canvas,
            f"{self.init_type} init",
            px,
            py - 16.0,
            font_size=self.font_size,
            color=DLTheme.TEXT_DIM,
        )

        mx = px + self.hist_width + 40.0
        my = py
        matrix_vals: list[list[float]] = []
        idx = 0
        for r in range(self.matrix_rows):
            row: list[float] = []
            for _c in range(self.matrix_cols):
                row.append(samples[idx] if idx < len(samples) else 0.0)
                idx += 1
            matrix_vals.append(row)

        for r in range(self.matrix_rows):
            for c in range(self.matrix_cols):
                cx = mx + c * (self.cell_size + self.gap)
                cy = my + r * (self.cell_size + self.gap)
                label = format_float(matrix_vals[r][c], precision=1)
                draw_round_cell(
                    canvas,
                    cx,
                    cy,
                    self.cell_size,
                    label=label,
                    fill_color=DLTheme.BG,
                    stroke_color=self.matrix_color,
                    font_size=self.font_size * 0.85,
                    radius=4.0,
                )

        draw_label(canvas, "weights W", mx, my - 14.0, font_size=self.font_size, color=DLTheme.TEXT)


@dataclass(slots=True)
class EarlyStopping(Node):
    """Train/validation loss curves with a marker at the best epoch."""

    train_loss: list[float] = field(
        default_factory=lambda: [1.2, 0.9, 0.7, 0.55, 0.48, 0.44, 0.42, 0.41],
    )
    val_loss: list[float] = field(
        default_factory=lambda: [1.3, 1.0, 0.82, 0.68, 0.62, 0.61, 0.64, 0.7],
    )
    best_epoch: int = 5
    progress: float = 1.0
    width: float = 300.0
    height: float = 180.0
    train_color: str = DLTheme.BLUE
    val_color: str = DLTheme.RED
    stop_color: str = DLTheme.YELLOW
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        if not self.train_loss:
            return

        draw_plot_border(canvas, px, py, self.width, self.height)
        n = len(self.train_loss)
        all_vals = list(self.train_loss) + list(self.val_loss)
        y_min = min(all_vals) * 0.9
        y_max = max(all_vals) * 1.1
        span = y_max - y_min if y_max > y_min else 1.0

        def to_screen(epoch: int, loss: float) -> tuple[float, float]:
            tx = epoch / max(1, n - 1)
            ty = (loss - y_min) / span
            return px + tx * self.width, py + self.height - ty * self.height

        def draw_series(losses: list[float], color: str) -> None:
            if stroke_line is None or len(losses) < 2:
                return
            limit = max(1, int(max(0.0, min(1.0, self.progress)) * (len(losses) - 1)) + 1)
            prev: tuple[float, float] | None = None
            for i in range(limit):
                pt = to_screen(i, losses[i])
                if prev is not None:
                    stroke_line(prev[0], prev[1], pt[0], pt[1], color, 2.0)
                prev = pt

        draw_series(self.train_loss, self.train_color)
        draw_series(self.val_loss, self.val_color)

        if 0 <= self.best_epoch < n and stroke_line is not None:
            bx, _ = to_screen(self.best_epoch, y_min)
            stroke_line(
                bx,
                py,
                bx,
                py + self.height,
                self.stop_color,
                2.0,
                dash_pattern=(5.0, 4.0),
            )
            draw_label(
                canvas,
                "stop",
                bx + 4.0,
                py + 8.0,
                font_size=self.font_size * 0.9,
                color=self.stop_color,
            )

        draw_label(canvas, "train", px + 8.0, py + 8.0, font_size=self.font_size, color=self.train_color)
        draw_label(canvas, "val", px + 52.0, py + 8.0, font_size=self.font_size, color=self.val_color)


@dataclass(slots=True)
class Regularization(Node):
    """Loss contours with L1 (diamond) and L2 (circle) constraint regions."""

    width: float = 260.0
    height: float = 260.0
    l1_scale: float = 70.0
    l2_scale: float = 85.0
    contour_color: str = DLTheme.GRID
    l1_color: str = DLTheme.RED
    l2_color: str = DLTheme.BLUE
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        fill_ellipse = getattr(canvas, "fill_ellipse", None)
        fill_polygon = getattr(canvas, "fill_polygon", None)

        cx = px + self.width / 2.0
        cy = py + self.height / 2.0

        if fill_ellipse is not None:
            for r in (40.0, 70.0, 100.0, 120.0):
                fill_ellipse(
                    cx,
                    cy,
                    r,
                    r * 0.65,
                    fill_color="#00000000",
                    stroke_color=self.contour_color,
                    stroke_width=1.0,
                )

        s = self.l1_scale
        if fill_polygon is not None:
            fill_polygon(
                [cx, cx + s, cx, cx - s],
                [cy - s, cy, cy + s, cy],
                fill_color="#e06c7522",
                stroke_color=self.l1_color,
                stroke_width=2.0,
            )
        elif stroke_line is not None:
            diamond = [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy), (cx, cy - s)]
            for i in range(len(diamond) - 1):
                stroke_line(
                    diamond[i][0],
                    diamond[i][1],
                    diamond[i + 1][0],
                    diamond[i + 1][1],
                    self.l1_color,
                    2.0,
                )

        if fill_ellipse is not None:
            fill_ellipse(
                cx,
                cy,
                self.l2_scale,
                self.l2_scale,
                fill_color="#61afef22",
                stroke_color=self.l2_color,
                stroke_width=2.0,
            )

        draw_label(canvas, "L1", cx - self.l1_scale - 28.0, cy, font_size=self.font_size, color=self.l1_color)
        draw_label(canvas, "L2", cx + self.l2_scale + 8.0, cy - 8.0, font_size=self.font_size, color=self.l2_color)
        draw_label(
            canvas,
            "regularization",
            px,
            py - 16.0,
            font_size=self.font_size,
            color=DLTheme.TEXT_DIM,
        )


@dataclass(slots=True)
class Dropout(Node):
    """Neural network with dropped neurons greyed and crossed out."""

    layer_sizes: list[int] = field(default_factory=lambda: [4, 5, 3])
    dropped_indices: set[tuple[int, int]] = field(default_factory=set)
    node_radius: float = 18.0
    layer_spacing: float = 110.0
    node_spacing: float = 48.0
    progress: float = 1.0
    active_color: str = DLTheme.CYAN
    dropped_color: str = DLTheme.TEXT_DIM
    neuron_fill: str = DLTheme.BG_DEEP
    weight_color: str = DLTheme.GRID
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        stroke_line = getattr(canvas, "stroke_line", None)
        if not self.layer_sizes:
            return

        positions = _neuron_positions(
            self.layer_sizes,
            px,
            py,
            layer_spacing=self.layer_spacing,
            node_spacing=self.node_spacing,
        )
        n_layers = len(self.layer_sizes)
        show_drop = self.progress >= 0.5

        if stroke_line is not None:
            for li in range(n_layers - 1):
                for ni, (x0, y0) in enumerate(positions[li]):
                    if show_drop and (li, ni) in self.dropped_indices:
                        continue
                    for nj, (x1, y1) in enumerate(positions[li + 1]):
                        if show_drop and (li + 1, nj) in self.dropped_indices:
                            continue
                        stroke_line(
                            x0 + self.node_radius,
                            y0,
                            x1 - self.node_radius,
                            y1,
                            self.weight_color,
                            1.0,
                        )

        for li, pts in enumerate(positions):
            for ni, (nx, ny) in enumerate(pts):
                is_dropped = show_drop and (li, ni) in self.dropped_indices
                fill = DLTheme.BG if is_dropped else self.neuron_fill
                stroke = self.dropped_color if is_dropped else self.active_color
                _draw_neuron(canvas, nx, ny, self.node_radius, fill=fill, stroke=stroke)
                if is_dropped:
                    _draw_cross(canvas, nx, ny, self.node_radius, self.dropped_color)

        draw_label(
            canvas,
            "dropout",
            px,
            py - self.node_radius - 22.0,
            font_size=self.font_size,
            color=DLTheme.TEXT_DIM,
        )

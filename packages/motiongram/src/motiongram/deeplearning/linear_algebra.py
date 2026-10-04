"""Visual components for linear algebra in deep learning."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, cast

from motiongram.core import Node
from motiongram.canvas import Canvas


@dataclass(slots=True)
class Scalars(Node):
    """Visualizer for a single scalar value in deep learning (e.g. learning rate, loss value)."""

    value: float | int | str = 0.0
    label: str = ""
    fill_color: str = "#21252b"
    stroke_color: str = "#61afef"
    stroke_width: float = 2.0
    text_color: str = "#abb2bf"
    label_color: str = "#5c6370"
    box_size: float = 60.0
    font_size: float = 18.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        draw_text = getattr(canvas, "draw_text", None)

        # Draw box
        if fill_round_rect is not None:
            fill_round_rect(
                px,
                py,
                px + self.box_size,
                py + self.box_size,
                8.0,
                fill_color=self.fill_color,
                stroke_color=self.stroke_color if self.stroke_width > 0 else None,
                stroke_width=self.stroke_width,
            )

        # Draw value centered
        val_str = str(self.value)
        if isinstance(self.value, float):
            val_str = f"{self.value:.2f}"

        if draw_text is not None:
            # Simple center approximation (x - half width, y - half height)
            val_len = len(val_str)
            tx = px + (self.box_size - val_len * (self.font_size * 0.55)) / 2.0
            ty = py + (self.box_size - self.font_size) / 2.0
            draw_text(val_str, tx, ty, self.font_size, self.text_color)

            # Draw label above
            if self.label:
                lx = px + (self.box_size - len(self.label) * (self.font_size * 0.45)) / 2.0
                ly = py - self.font_size - 6.0
                draw_text(self.label, lx, ly, self.font_size * 0.8, self.label_color)


@dataclass(slots=True)
class Vectors(Node):
    """Visualizer for a 1D vector of numbers. Supports horizontal/vertical formats."""

    values: list[float | int | str] = field(default_factory=list)
    horizontal: bool = True
    label: str = ""
    fill_color: str = "#21252b"
    stroke_color: str = "#56b6c2"
    stroke_width: float = 1.5
    text_color: str = "#abb2bf"
    label_color: str = "#5c6370"
    cell_size: float = 48.0
    gap: float = 4.0
    highlight_indices: list[int] = field(default_factory=list)
    highlight_color: str = "#98c379"
    highlight_text_color: str = "#282c34"
    font_size: float = 16.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        draw_text = getattr(canvas, "draw_text", None)

        if not self.values:
            return

        hl_set = set(self.highlight_indices)

        for i, val in enumerate(self.values):
            # Calculate coordinates
            if self.horizontal:
                cx = px + i * (self.cell_size + self.gap)
                cy = py
            else:
                cx = px
                cy = py + i * (self.cell_size + self.gap)

            is_hl = i in hl_set
            cell_fill = self.highlight_color if is_hl else self.fill_color
            cell_stroke = self.stroke_color
            cell_text = self.highlight_text_color if is_hl else self.text_color

            if fill_round_rect is not None:
                fill_round_rect(
                    cx,
                    cy,
                    cx + self.cell_size,
                    cy + self.cell_size,
                    6.0,
                    fill_color=cell_fill,
                    stroke_color=cell_stroke if self.stroke_width > 0 else None,
                    stroke_width=self.stroke_width,
                )

            val_str = str(val)
            if isinstance(val, float):
                val_str = f"{val:.1f}"

            if draw_text is not None:
                tx = cx + (self.cell_size - len(val_str) * (self.font_size * 0.55)) / 2.0
                ty = cy + (self.cell_size - self.font_size) / 2.0
                draw_text(val_str, tx, ty, self.font_size, cell_text)

        # Draw label
        if self.label and draw_text is not None:
            if self.horizontal:
                lx = px
                ly = py - self.font_size - 8.0
            else:
                lx = px + self.cell_size + 10.0
                ly = py
            draw_text(self.label, lx, ly, self.font_size * 0.9, self.label_color)


@dataclass(slots=True)
class Matrices(Node):
    """Visualizer for a 2D matrix of numbers. Ideal for weights, activations."""

    values: list[list[float | int | str]] = field(default_factory=list)
    label: str = ""
    fill_color: str = "#21252b"
    stroke_color: str = "#abb2bf"
    stroke_width: float = 1.0
    text_color: str = "#abb2bf"
    label_color: str = "#5c6370"
    cell_size: float = 44.0
    gap: float = 3.0
    highlight_cells: list[tuple[int, int]] = field(default_factory=list)
    highlight_row: int | None = None
    highlight_col: int | None = None
    highlight_color: str = "#e5c07b"
    highlight_text_color: str = "#282c34"
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        draw_text = getattr(canvas, "draw_text", None)

        if not self.values or not self.values[0]:
            return

        rows = len(self.values)
        cols = len(self.values[0])
        hl_cells = set(self.highlight_cells)

        for r in range(rows):
            for c in range(cols):
                cx = px + c * (self.cell_size + self.gap)
                cy = py + r * (self.cell_size + self.gap)

                is_hl = (
                    (r, c) in hl_cells
                    or r == self.highlight_row
                    or c == self.highlight_col
                )

                cell_fill = self.highlight_color if is_hl else self.fill_color
                cell_text = self.highlight_text_color if is_hl else self.text_color

                if fill_round_rect is not None:
                    fill_round_rect(
                        cx,
                        cy,
                        cx + self.cell_size,
                        cy + self.cell_size,
                        4.0,
                        fill_color=cell_fill,
                        stroke_color=self.stroke_color if self.stroke_width > 0 else None,
                        stroke_width=self.stroke_width,
                    )

                val = self.values[r][c]
                val_str = str(val)
                if isinstance(val, float):
                    val_str = f"{val:.1f}"

                if draw_text is not None:
                    tx = cx + (self.cell_size - len(val_str) * (self.font_size * 0.55)) / 2.0
                    ty = cy + (self.cell_size - self.font_size) / 2.0
                    draw_text(val_str, tx, ty, self.font_size, cell_text)

        # Draw label
        if self.label and draw_text is not None:
            lx = px
            ly = py - self.font_size - 10.0
            draw_text(self.label, lx, ly, self.font_size * 1.1, self.label_color)


@dataclass(slots=True)
class Tensors(Node):
    """Visualizer for a 3D tensor, rendered as a stack of matrices with depth offsets."""

    matrices_values: list[list[list[float | int | str]]] = field(default_factory=list)
    cell_size: float = 36.0
    gap: float = 2.0
    depth_offset: tuple[float, float] = (16.0, -16.0)  # dx, dy for layer stack
    fill_color: str = "#282c34"
    stroke_color: str = "#c678dd"
    stroke_width: float = 1.0
    text_color: str = "#abb2bf"
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        if not self.matrices_values:
            return

        # Render from back (index 0 or last) to front for correct overlapping
        # Let's render index 0 at the back and subsequent matrices overlapping towards front
        for layer_idx in range(len(self.matrices_values)):
            m_vals = self.matrices_values[layer_idx]
            offset_x = layer_idx * self.depth_offset[0]
            offset_y = layer_idx * self.depth_offset[1]

            # We can compose a matrix subnode or draw it manually
            # Let's draw it manually with a slight opacity fade to back layers
            opacity_mult = 0.6 + 0.4 * (layer_idx + 1) / len(self.matrices_values)

            # Let's use Matrices visualizer locally to draw
            mat = Matrices(
                values=m_vals,
                fill_color=self.fill_color,
                stroke_color=self.stroke_color,
                stroke_width=self.stroke_width,
                text_color=self.text_color,
                cell_size=self.cell_size,
                gap=self.gap,
                font_size=self.font_size,
            )
            # Since draw is slot based, we call draw_world directly
            mat.draw(canvas, px + offset_x, py + offset_y)


@dataclass(slots=True)
class DotProducts(Node):
    """Visualizes dot product calculation between Vector A and Vector B."""

    vec_a: list[float] = field(default_factory=list)
    vec_b: list[float] = field(default_factory=list)
    progress: float = 0.0  # 0 to 1 drives the step-by-step element connecting highlight
    cell_size: float = 44.0
    gap: float = 6.0
    color_a: str = "#61afef"
    color_b: str = "#c678dd"
    stroke_color: str = "#5c6370"
    active_color: str = "#e5c07b"
    font_size: float = 15.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        stroke_line = getattr(canvas, "stroke_line", None)
        draw_text = getattr(canvas, "draw_text", None)

        n = min(len(self.vec_a), len(self.vec_b))
        if n == 0:
            return

        # Position Vector A horizontally at top
        # Position Vector B horizontally at bottom with some space
        y_a = py
        y_b = py + 120.0

        # Current active index based on progress
        active_idx = min(int(self.progress * n), n - 1) if self.progress < 1.0 else -1
        is_completed = self.progress >= 1.0

        # Draw Vector A
        vec_node_a = Vectors(
            values=cast(list[Any], self.vec_a),
            horizontal=True,
            fill_color="#21252b",
            stroke_color=self.color_a,
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_indices=[active_idx] if active_idx != -1 else [],
            highlight_color=self.active_color,
            font_size=self.font_size,
        )
        vec_node_a.draw(canvas, px, y_a)

        # Draw Vector B
        vec_node_b = Vectors(
            values=cast(list[Any], self.vec_b),
            horizontal=True,
            fill_color="#21252b",
            stroke_color=self.color_b,
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_indices=[active_idx] if active_idx != -1 else [],
            highlight_color=self.active_color,
            font_size=self.font_size,
        )
        vec_node_b.draw(canvas, px, y_b)

        # Draw connecting lines and multiply labels
        for i in range(n):
            cx_a = px + i * (self.cell_size + self.gap) + self.cell_size / 2.0
            cy_a = y_a + self.cell_size
            cx_b = px + i * (self.cell_size + self.gap) + self.cell_size / 2.0
            cy_b = y_b

            is_active = (i == active_idx)
            is_past = (i < active_idx) or is_completed
            line_color = self.active_color if is_active else (self.color_a if is_past else self.stroke_color)
            line_width = 2.5 if is_active else (1.5 if is_past else 1.0)

            if stroke_line is not None:
                stroke_line(cx_a, cy_a, cx_b, cy_b, line_color, line_width)

        # Draw the arithmetic formula at the bottom
        if draw_text is not None:
            formula_y = y_b + self.cell_size + 40.0
            terms = []
            running_sum = 0.0
            limit = active_idx + 1 if active_idx != -1 else (n if is_completed else 0)

            for i in range(limit):
                running_sum += self.vec_a[i] * self.vec_b[i]
                terms.append(f"({self.vec_a[i]:.1f} * {self.vec_b[i]:.1f})")

            formula_str = " + ".join(terms)
            if formula_str:
                formula_str += f" = {running_sum:.2f}"
            else:
                formula_str = "A * B = ?"

            draw_text(formula_str, px, formula_y, self.font_size * 1.1, self.active_color if is_completed else "#abb2bf")


@dataclass(slots=True)
class VectorProducts(Node):
    """Visualizes vector outer product (u * v^T) or matrix-vector product."""

    vec_u: list[float] = field(default_factory=list)
    vec_v: list[float] = field(default_factory=list)
    cell_size: float = 40.0
    gap: float = 4.0
    color_u: str = "#61afef"
    color_v: str = "#c678dd"
    color_out: str = "#98c379"
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        draw_text = getattr(canvas, "draw_text", None)

        if not self.vec_u or not self.vec_v:
            return

        rows = len(self.vec_u)
        cols = len(self.vec_v)

        # Draw vec_u as a vertical column at left
        u_node = Vectors(
            values=cast(list[Any], self.vec_u),
            horizontal=False,
            fill_color="#21252b",
            stroke_color=self.color_u,
            cell_size=self.cell_size,
            gap=self.gap,
            font_size=self.font_size,
        )
        u_node.draw(canvas, px, py + self.cell_size + self.gap * 2.0)

        # Draw vec_v as a horizontal row at top
        v_node = Vectors(
            values=cast(list[Any], self.vec_v),
            horizontal=True,
            fill_color="#21252b",
            stroke_color=self.color_v,
            cell_size=self.cell_size,
            gap=self.gap,
            font_size=self.font_size,
        )
        v_node.draw(canvas, px + self.cell_size + self.gap * 2.0, py)

        # Compute outer product matrix values
        matrix_vals = [[0.0] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                matrix_vals[r][c] = self.vec_u[r] * self.vec_v[c]

        # Draw outer product matrix in the center/bottom-right
        mat_node = Matrices(
            values=cast(list[list[Any]], matrix_vals),
            fill_color="#21252b",
            stroke_color=self.color_out,
            cell_size=self.cell_size,
            gap=self.gap,
            font_size=self.font_size,
        )
        mat_node.draw(canvas, px + self.cell_size + self.gap * 2.0, py + self.cell_size + self.gap * 2.0)

        if draw_text is not None:
            draw_text("u", px + 10.0, py, self.font_size, self.color_u)
            draw_text("v^T", px + self.cell_size + 10.0, py - 20.0, self.font_size, self.color_v)
            draw_text("u * v^T (Outer Product)", px + self.cell_size * 2.0, py + self.cell_size * (rows + 1) + 30.0, self.font_size * 1.1, self.color_out)


@dataclass(slots=True)
class MatrixMultiplication(Node):
    """Visualizes matrix multiplication C = A * B with active row/col highlights."""

    matrix_a: list[list[float]] = field(default_factory=list)
    matrix_b: list[list[float]] = field(default_factory=list)
    active_row: int | None = 0
    active_col: int | None = 0
    cell_size: float = 38.0
    gap: float = 3.0
    color_a: str = "#61afef"
    color_b: str = "#c678dd"
    color_c: str = "#98c379"
    highlight_color: str = "#e5c07b"
    font_size: float = 12.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        draw_text = getattr(canvas, "draw_text", None)

        if not self.matrix_a or not self.matrix_b:
            return

        r_a, c_a = len(self.matrix_a), len(self.matrix_a[0])
        r_b, c_b = len(self.matrix_b), len(self.matrix_b[0])

        if c_a != r_b:
            return  # Inner dimensions must match

        # Layout placements:
        # A is on the left
        # B is placed high on the right
        # C is placed below B, aligned with A's rows and B's columns! (standard layout)
        offset_x_b = (c_a + 2) * (self.cell_size + self.gap)
        offset_y_c = (r_b + 2) * (self.cell_size + self.gap)

        # Draw Matrix A
        mat_a = Matrices(
            values=cast(list[list[Any]], self.matrix_a),
            fill_color="#21252b",
            stroke_color=self.color_a,
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_row=self.active_row,
            highlight_color=self.highlight_color,
            font_size=self.font_size,
            label="Matrix A",
        )
        mat_a.draw(canvas, px, py + offset_y_c)

        # Draw Matrix B
        mat_b = Matrices(
            values=cast(list[list[Any]], self.matrix_b),
            fill_color="#21252b",
            stroke_color=self.color_b,
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_col=self.active_col,
            highlight_color=self.highlight_color,
            font_size=self.font_size,
            label="Matrix B",
        )
        mat_b.draw(canvas, px + offset_x_b, py)

        # Compute output Matrix C
        matrix_c = [[0.0] * c_b for _ in range(r_a)]
        for r in range(r_a):
            for c in range(c_b):
                s = 0.0
                for k in range(c_a):
                    s += self.matrix_a[r][k] * self.matrix_b[k][c]
                matrix_c[r][c] = s

        # Draw Matrix C
        # If active_row and active_col are set, highlight that cell in C
        hl_cells = []
        if self.active_row is not None and self.active_col is not None:
            hl_cells.append((self.active_row, self.active_col))

        mat_c = Matrices(
            values=cast(list[list[Any]], matrix_c),
            fill_color="#21252b",
            stroke_color=self.color_c,
            cell_size=self.cell_size,
            gap=self.gap,
            highlight_cells=hl_cells,
            highlight_color=self.highlight_color,
            font_size=self.font_size,
            label="Matrix C = A * B",
        )
        mat_c.draw(canvas, px + offset_x_b, py + offset_y_c)

        # Draw dotted guides showing how active row of A and active col of B map to C cell
        if (self.active_row is not None and self.active_col is not None and
                getattr(canvas, "stroke_line", None) is not None):
            stroke_line = canvas.stroke_line

            # Center of active row in A
            row_y = py + offset_y_c + self.active_row * (self.cell_size + self.gap) + self.cell_size / 2.0
            end_x_a = px + c_a * (self.cell_size + self.gap)

            # Center of active col in B
            col_x = px + offset_x_b + self.active_col * (self.cell_size + self.gap) + self.cell_size / 2.0
            end_y_b = py + r_b * (self.cell_size + self.gap)

            # Destination cell in C
            dest_x = px + offset_x_b + self.active_col * (self.cell_size + self.gap) + self.cell_size / 2.0
            dest_y = py + offset_y_c + self.active_row * (self.cell_size + self.gap) + self.cell_size / 2.0

            # Draw dashed lines
            stroke_line(end_x_a, row_y, dest_x, row_y, self.highlight_color, 1.5, dash_pattern=(4.0, 4.0))
            stroke_line(col_x, end_y_b, col_x, dest_y, self.highlight_color, 1.5, dash_pattern=(4.0, 4.0))

            # Display active cell dot product math below
            if draw_text is not None:
                terms = []
                for k in range(c_a):
                    terms.append(f"({self.matrix_a[self.active_row][k]:.1f} * {self.matrix_b[k][self.active_col]:.1f})")
                eq_str = " + ".join(terms) + f" = {matrix_c[self.active_row][self.active_col]:.2f}"
                draw_text(
                    f"C[{self.active_row},{self.active_col}] = " + eq_str,
                    px,
                    py + offset_y_c + r_a * (self.cell_size + self.gap) + 40.0,
                    self.font_size * 1.1,
                    self.highlight_color,
                )

"""Lecture slide outlines and ML pipeline / training-loop visual components."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from motiongram.core import Node
from motiongram.canvas import Canvas
from motiongram.deeplearning._draw import (
    DLTheme,
    draw_arrow,
    draw_label,
    draw_round_cell,
)


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _draw_slide_frame(
    canvas: Canvas,
    px: float,
    py: float,
    *,
    title: str,
    bullets: list[str],
    accent: str,
    width: float,
    height: float,
    font_size: float,
) -> None:
    """Shared lecture-slide chrome: frame, title bar, bullet placeholders."""
    fill_round_rect = getattr(canvas, "fill_round_rect", None)
    stroke_line = getattr(canvas, "stroke_line", None)

    if fill_round_rect is not None:
        fill_round_rect(px, py, px + width, py + height, 10.0, fill_color=DLTheme.BG_DEEP, stroke_color=accent, stroke_width=2.0)
        fill_round_rect(px, py, px + width, py + 36.0, 10.0, fill_color=accent, stroke_color=None, stroke_width=0.0)

    draw_label(canvas, title, px + 14.0, py + 10.0, font_size=font_size, color=DLTheme.BG_DEEP)

    line_y = py + 48.0
    for i, bullet in enumerate(bullets):
        text = bullet if bullet else f"• bullet {i + 1} …"
        draw_label(
            canvas,
            text,
            px + 20.0,
            line_y,
            font_size=font_size * 0.92,
            color=DLTheme.TEXT_DIM if not bullet else DLTheme.TEXT,
        )
        if stroke_line is not None and not bullet:
            stroke_line(
                px + 20.0,
                line_y + font_size,
                px + width - 24.0,
                line_y + font_size,
                DLTheme.GRID,
                1.0,
                dash_pattern=(5.0, 4.0),
            )
        line_y += font_size + 14.0


@dataclass(slots=True)
class Intuition(Node):
    """Lecture slide: intuitive overview of an algorithm."""

    title: str = "Intuition"
    bullets: list[str] = field(default_factory=lambda: ["", "", ""])
    width: float = 280.0
    height: float = 200.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_slide_frame(
            canvas,
            px,
            py,
            title=self.title,
            bullets=self.bullets,
            accent=DLTheme.CYAN,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class Theory(Node):
    """Lecture slide: formal theory and notation."""

    title: str = "Theory"
    bullets: list[str] = field(default_factory=lambda: ["", "", ""])
    width: float = 280.0
    height: float = 200.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_slide_frame(
            canvas,
            px,
            py,
            title=self.title,
            bullets=self.bullets,
            accent=DLTheme.BLUE,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class ScratchImplementation(Node):
    """Lecture slide: from-scratch implementation walkthrough."""

    title: str = "Scratch implementation"
    bullets: list[str] = field(default_factory=lambda: ["", "", ""])
    width: float = 280.0
    height: float = 200.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_slide_frame(
            canvas,
            px,
            py,
            title=self.title,
            bullets=self.bullets,
            accent=DLTheme.YELLOW,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class PracticalImplementation(Node):
    """Lecture slide: practical / library-based implementation."""

    title: str = "Practical implementation"
    bullets: list[str] = field(default_factory=lambda: ["", "", ""])
    width: float = 280.0
    height: float = 200.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_slide_frame(
            canvas,
            px,
            py,
            title=self.title,
            bullets=self.bullets,
            accent=DLTheme.GREEN,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class Summary(Node):
    """Lecture slide: recap and key takeaways."""

    title: str = "Summary"
    bullets: list[str] = field(default_factory=lambda: ["", "", ""])
    width: float = 280.0
    height: float = 200.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_slide_frame(
            canvas,
            px,
            py,
            title=self.title,
            bullets=self.bullets,
            accent=DLTheme.PURPLE,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class WhatIsMissing(Node):
    """Lecture slide: limitations and future work."""

    title: str = "What is missing"
    bullets: list[str] = field(default_factory=lambda: ["", "", ""])
    width: float = 280.0
    height: float = 200.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_slide_frame(
            canvas,
            px,
            py,
            title=self.title,
            bullets=self.bullets,
            accent=DLTheme.RED,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


def _draw_pipeline_box(
    canvas: Canvas,
    px: float,
    py: float,
    *,
    icon: str,
    label: str,
    accent: str,
    width: float,
    height: float,
    font_size: float,
) -> None:
    fill_round_rect = getattr(canvas, "fill_round_rect", None)
    if fill_round_rect is not None:
        fill_round_rect(
            px,
            py,
            px + width,
            py + height,
            8.0,
            fill_color=DLTheme.BG,
            stroke_color=accent,
            stroke_width=2.0,
        )
    draw_label(
        canvas,
        icon,
        px + (width - len(icon) * (font_size * 0.5)) / 2.0,
        py + (height - font_size) / 2.0,
        font_size=font_size + 4.0,
        color=accent,
    )
    draw_label(canvas, label, px + 6.0, py + height + 6.0, font_size=font_size * 0.9, color=DLTheme.TEXT)


@dataclass(slots=True)
class DataSet(Node):
    """Pipeline box: dataset source."""

    label: str = "Dataset"
    icon: str = "📊"
    width: float = 88.0
    height: float = 56.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_pipeline_box(
            canvas,
            px,
            py,
            icon=self.icon,
            label=self.label,
            accent=DLTheme.CYAN,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class Model(Node):
    """Pipeline box: model architecture."""

    label: str = "Model"
    icon: str = "🧠"
    width: float = 88.0
    height: float = 56.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_pipeline_box(
            canvas,
            px,
            py,
            icon=self.icon,
            label=self.label,
            accent=DLTheme.BLUE,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class Training(Node):
    """Pipeline box: training step."""

    label: str = "Training"
    icon: str = "⚙"
    width: float = 88.0
    height: float = 56.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_pipeline_box(
            canvas,
            px,
            py,
            icon=self.icon,
            label=self.label,
            accent=DLTheme.GREEN,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class LossFunction(Node):
    """Pipeline box: loss / objective."""

    label: str = "Loss"
    icon: str = "📉"
    width: float = 88.0
    height: float = 56.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_pipeline_box(
            canvas,
            px,
            py,
            icon=self.icon,
            label=self.label,
            accent=DLTheme.RED,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class OptimizationAlgorithm(Node):
    """Pipeline box: optimizer (SGD, Adam, …)."""

    label: str = "Optimizer"
    icon: str = "↘"
    width: float = 88.0
    height: float = 56.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_pipeline_box(
            canvas,
            px,
            py,
            icon=self.icon,
            label=self.label,
            accent=DLTheme.YELLOW,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class TrainTestSplit(Node):
    """Pipeline box: train / test split."""

    label: str = "Train / test split"
    icon: str = "✂"
    width: float = 88.0
    height: float = 56.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_pipeline_box(
            canvas,
            px,
            py,
            icon=self.icon,
            label=self.label,
            accent=DLTheme.PURPLE,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


@dataclass(slots=True)
class CrossVal(Node):
    """Pipeline box: cross-validation folds."""

    label: str = "Cross-val"
    icon: str = "🔁"
    width: float = 88.0
    height: float = 56.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        _draw_pipeline_box(
            canvas,
            px,
            py,
            icon=self.icon,
            label=self.label,
            accent=DLTheme.HIGHLIGHT,
            width=self.width,
            height=self.height,
            font_size=self.font_size,
        )


_LOOP_COMPONENTS: tuple[tuple[str, str, str], ...] = (
    ("Dataset", "📊", DLTheme.CYAN),
    ("Model", "🧠", DLTheme.BLUE),
    ("Loss", "📉", DLTheme.RED),
    ("Optimizer", "↘", DLTheme.YELLOW),
    ("Training", "⚙", DLTheme.GREEN),
)


@dataclass(slots=True)
class TrainingLoop(Node):
    """Circular training loop connecting dataset → model → loss → optimizer → training.

    ``progress`` in ``[0, 1]`` animates a highlight pulse traveling around the loop.
    """

    progress: float = 0.0
    radius: float = 110.0
    box_size: float = 72.0
    font_size: float = 13.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        cx = px + self.radius + self.box_size / 2.0
        cy = py + self.radius + self.box_size / 2.0
        n = len(_LOOP_COMPONENTS)
        prog = _clamp01(self.progress)
        active_seg = int(prog * n) % n if prog < 1.0 else 0
        pulse = 0.5 + 0.5 * math.sin(prog * math.pi * 2.0 * n)

        draw_label(canvas, "Training loop", px, py - self.font_size - 6.0, font_size=self.font_size + 1.0, color=DLTheme.TEXT)

        centers: list[tuple[float, float]] = []
        for i in range(n):
            angle = -math.pi / 2.0 + (2.0 * math.pi * i) / n
            bx = cx + self.radius * math.cos(angle) - self.box_size / 2.0
            by = cy + self.radius * math.sin(angle) - self.box_size / 2.0
            centers.append((bx + self.box_size / 2.0, by + self.box_size / 2.0))

        for i in range(n):
            x0, y0 = centers[i]
            x1, y1 = centers[(i + 1) % n]
            seg_active = i == active_seg or (prog >= 1.0 and i == n - 1)
            color = DLTheme.HIGHLIGHT if seg_active else DLTheme.TEXT_DIM
            width = 2.5 + pulse if seg_active else 1.5
            draw_arrow(canvas, x0, y0, x1, y1, color=color, width=width)

        for i, (label, icon, accent) in enumerate(_LOOP_COMPONENTS):
            angle = -math.pi / 2.0 + (2.0 * math.pi * i) / n
            bx = cx + self.radius * math.cos(angle) - self.box_size / 2.0
            by = cy + self.radius * math.sin(angle) - self.box_size / 2.0
            is_active = i == active_seg
            draw_round_cell(
                canvas,
                bx,
                by,
                self.box_size,
                label=icon,
                fill_color=DLTheme.GLOW if is_active else DLTheme.BG,
                stroke_color=DLTheme.HIGHLIGHT if is_active else accent,
                stroke_width=3.0 if is_active else 2.0,
                text_color=accent,
                font_size=self.font_size + 6.0,
                radius=8.0,
            )
            draw_label(
                canvas,
                label,
                bx,
                by + self.box_size + 4.0,
                font_size=self.font_size * 0.85,
                color=DLTheme.HIGHLIGHT if is_active else DLTheme.TEXT,
            )

        fill_ellipse = getattr(canvas, "fill_ellipse", None)
        if fill_ellipse is not None and prog > 0.0:
            ax, ay = centers[active_seg]
            glow_r = 6.0 + 4.0 * pulse
            fill_ellipse(ax, ay, glow_r, glow_r, fill_color=DLTheme.GLOW)

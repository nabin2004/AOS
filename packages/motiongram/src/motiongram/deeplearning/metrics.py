"""Classification metrics and prediction output visual components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from motiongram.core import Node
from motiongram.canvas import Canvas
from motiongram.deeplearning._draw import (
    DLTheme,
    draw_label,
    draw_round_cell,
    format_float,
)

MetricsMode = Literal["confusion", "cards"]


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _metric_from_counts(tp: int, fp: int, fn: int, tn: int) -> dict[str, float]:
    total = tp + fp + fn + tn
    acc = (tp + tn) / total if total else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


@dataclass(slots=True)
class Metrics(Node):
    """Classifier evaluation: 2×2 confusion matrix or metric cards with progress bars.

    Set ``mode`` to ``"confusion"`` for TP/FP/FN/TN grid, or ``"cards"`` for
    accuracy, precision, recall, and F1 with animated fill bars driven by ``progress``.
    """

    mode: MetricsMode = "confusion"
    tp: int = 42
    fp: int = 8
    fn: int = 5
    tn: int = 45
    progress: float = 1.0
    width: float = 320.0
    height: float = 220.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        draw_label(canvas, "Metrics", px, py - self.font_size - 8.0, font_size=self.font_size + 1.0, color=DLTheme.TEXT)

        if self.mode == "confusion":
            self._draw_confusion(canvas, px, py)
        else:
            self._draw_cards(canvas, px, py)

    def _draw_confusion(self, canvas: Canvas, px: float, py: float) -> None:
        labels = (
            ("TP", self.tp, DLTheme.GREEN),
            ("FP", self.fp, DLTheme.RED),
            ("FN", self.fn, DLTheme.YELLOW),
            ("TN", self.tn, DLTheme.CYAN),
        )
        cell = min(self.width, self.height) / 2.0 - 8.0
        gap = 6.0

        draw_label(
            canvas,
            "pred +",
            px + cell + gap + cell / 2.0 - 20.0,
            py - 4.0,
            font_size=self.font_size * 0.85,
            color=DLTheme.TEXT_DIM,
        )
        draw_label(canvas, "actual +", px - 4.0, py + cell / 2.0, font_size=self.font_size * 0.85, color=DLTheme.TEXT_DIM)

        reveal = _clamp01(self.progress)
        for i, (abbr, count, color) in enumerate(labels):
            row, col = divmod(i, 2)
            cx = px + col * (cell + gap)
            cy = py + row * (cell + gap)
            shown = int(count * reveal) if self.progress < 1.0 else count
            draw_round_cell(
                canvas,
                cx,
                cy,
                cell,
                label="",
                fill_color=DLTheme.BG_DEEP,
                stroke_color=color,
                stroke_width=2.0,
                text_color=color,
                font_size=self.font_size,
                radius=8.0,
            )
            draw_label(canvas, abbr, cx + 10.0, cy + 10.0, font_size=self.font_size * 0.75, color=DLTheme.TEXT_DIM)
            draw_label(
                canvas,
                str(shown),
                cx + cell / 2.0 - 12.0,
                cy + cell / 2.0,
                font_size=self.font_size + 2.0,
                color=color,
            )

        counts = _metric_from_counts(self.tp, self.fp, self.fn, self.tn)
        summary = f"acc {format_float(counts['accuracy'], precision=2)}"
        draw_label(canvas, summary, px, py + 2 * (cell + gap) + 8.0, font_size=self.font_size * 0.9, color=DLTheme.TEXT_DIM)

    def _draw_cards(self, canvas: Canvas, px: float, py: float) -> None:
        counts = _metric_from_counts(self.tp, self.fp, self.fn, self.tn)
        items = (
            ("accuracy", counts["accuracy"], DLTheme.BLUE),
            ("precision", counts["precision"], DLTheme.CYAN),
            ("recall", counts["recall"], DLTheme.GREEN),
            ("f1", counts["f1"], DLTheme.PURPLE),
        )
        card_h = 40.0
        gap = 10.0
        bar_max_w = self.width - 100.0
        fill_round_rect = getattr(canvas, "fill_round_rect", None)
        prog = _clamp01(self.progress)

        for i, (name, value, color) in enumerate(items):
            cy = py + i * (card_h + gap)
            draw_label(canvas, name, px, cy + (card_h - self.font_size) / 2.0, font_size=self.font_size, color=DLTheme.TEXT)
            bar_x = px + 88.0
            bar_y = cy + 10.0
            bar_h = card_h - 20.0
            fill_w = bar_max_w * value * prog

            if fill_round_rect is not None:
                fill_round_rect(
                    bar_x,
                    bar_y,
                    bar_x + bar_max_w,
                    bar_y + bar_h,
                    4.0,
                    fill_color=DLTheme.BG_DEEP,
                    stroke_color=DLTheme.GRID,
                    stroke_width=1.0,
                )
                if fill_w > 0:
                    fill_round_rect(
                        bar_x,
                        bar_y,
                        bar_x + fill_w,
                        bar_y + bar_h,
                        4.0,
                        fill_color=color,
                        stroke_color=None,
                        stroke_width=0.0,
                    )

            draw_label(
                canvas,
                format_float(value * prog, precision=2),
                bar_x + bar_max_w + 8.0,
                cy + (card_h - self.font_size) / 2.0,
                font_size=self.font_size,
                color=color,
            )


@dataclass(slots=True)
class Prediction(Node):
    """Softmax-style class boxes with probabilities; ``predicted_idx`` is highlighted."""

    classes: list[str] = field(default_factory=lambda: ["cat", "dog", "bird"])
    probabilities: list[float] = field(default_factory=lambda: [0.12, 0.71, 0.17])
    predicted_idx: int = 1
    progress: float = 1.0
    width: float = 360.0
    box_height: float = 44.0
    gap: float = 8.0
    font_size: float = 14.0

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        n = len(self.classes)
        if n == 0:
            return

        probs = list(self.probabilities)
        while len(probs) < n:
            probs.append(0.0)
        probs = probs[:n]
        total = sum(probs) or 1.0
        probs = [p / total for p in probs]

        draw_label(canvas, "Prediction", px, py - self.font_size - 8.0, font_size=self.font_size + 1.0, color=DLTheme.TEXT)
        reveal = _clamp01(self.progress)
        pred_idx = max(0, min(self.predicted_idx, n - 1))
        fill_round_rect = getattr(canvas, "fill_round_rect", None)

        for i, (cls_name, prob) in enumerate(zip(self.classes, probs, strict=False)):
            cy = py + i * (self.box_height + self.gap)
            is_pred = i == pred_idx
            shown_prob = prob * reveal
            bar_inner = self.width - 24.0

            stroke = DLTheme.HIGHLIGHT if is_pred else DLTheme.GRID
            fill = DLTheme.GLOW if is_pred else DLTheme.BG_DEEP

            if fill_round_rect is not None:
                fill_round_rect(
                    px,
                    cy,
                    px + self.width,
                    cy + self.box_height,
                    6.0,
                    fill_color=fill,
                    stroke_color=stroke,
                    stroke_width=2.5 if is_pred else 1.0,
                )
                bar_w = bar_inner * shown_prob
                if bar_w > 1.0:
                    fill_round_rect(
                        px + 12.0,
                        cy + 8.0,
                        px + 12.0 + bar_w,
                        cy + self.box_height - 8.0,
                        3.0,
                        fill_color=DLTheme.BLUE if not is_pred else DLTheme.GREEN,
                        stroke_color=None,
                        stroke_width=0.0,
                    )

            name_color = DLTheme.HIGHLIGHT if is_pred else DLTheme.TEXT
            draw_label(canvas, cls_name, px + 14.0, cy + 6.0, font_size=self.font_size, color=name_color)
            pct = format_float(100.0 * shown_prob, precision=1) + "%"
            draw_label(
                canvas,
                pct,
                px + self.width - 56.0,
                cy + (self.box_height - self.font_size) / 2.0,
                font_size=self.font_size,
                color=DLTheme.GREEN if is_pred else DLTheme.CYAN,
            )

            if is_pred:
                draw_label(
                    canvas,
                    "★ predicted",
                    px + self.width - 120.0,
                    cy - 2.0,
                    font_size=self.font_size * 0.75,
                    color=DLTheme.HIGHLIGHT,
                )

"""Shared theme for manim-ai lecture visuals."""

from __future__ import annotations

from dataclasses import dataclass

from manim import BLUE, GREEN, GREY_B, ORANGE, PURPLE, RED, TEAL, WHITE, YELLOW


@dataclass(frozen=True)
class AITheme:
    background: str = "#1a1a2e"
    accent: str = "#e94560"
    primary: str = BLUE
    secondary: str = TEAL
    highlight: str = YELLOW
    positive: str = GREEN
    negative: str = RED
    soft: str = GREY_B
    neuron: str = WHITE
    edge: str = GREY_B
    attention: str = ORANGE
    residual: str = PURPLE
    title_size: int = 36
    body_size: int = 28
    math_size: int = 32


DEFAULT_THEME = AITheme()

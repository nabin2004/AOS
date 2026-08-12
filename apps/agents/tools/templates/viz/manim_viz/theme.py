"""Shared lecture theme for AOS Manim domain plugins."""

from __future__ import annotations

from dataclasses import dataclass

from manim import BLUE, GREEN, GREY_B, ORANGE, PURPLE, RED, TEAL, WHITE, YELLOW


@dataclass(frozen=True)
class VizTheme:
    background: str = "#1a1a2e"
    accent: str = "#e94560"
    primary: str = BLUE
    secondary: str = TEAL
    highlight: str = YELLOW
    positive: str = GREEN
    negative: str = RED
    soft: str = GREY_B
    force: str = ORANGE
    velocity: str = TEAL
    acceleration: str = PURPLE
    title_size: int = 36
    body_size: int = 28
    math_size: int = 32


DEFAULT_THEME = VizTheme()

from __future__ import annotations

from typing import Optional, List
from manim import (
    VGroup,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig


class BeamerColumn(VGroup):
    """A single column container inside BeamerColumns."""

    def __init__(self, width: float = 5.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.column_width = width


class BeamerColumns(VGroup):
    """Layout manager for side-by-side Beamer columns."""

    def __init__(self, *columns: BeamerColumn, buff: float = 0.5, **kwargs) -> None:
        super().__init__(**kwargs)
        for col in columns:
            self.add(col)
        self.arrange(RIGHT, buff=buff)

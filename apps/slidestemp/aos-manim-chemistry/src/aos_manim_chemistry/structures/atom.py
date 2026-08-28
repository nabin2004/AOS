from __future__ import annotations

from typing import Optional, Union
from manim import (
    VGroup,
    Circle,
    Text,
    ORIGIN,
)
from manim.utils.color import ManimColor
# pyrefly: ignore [missing-import]
from aos_manim_core import get_theme, ThemeConfig


# Standard CPK element colors
CPK_COLORS = {
    "H": "#FFFFFF",
    "C": "#334155",   # Slate dark
    "N": "#3B82F6",   # Blue
    "O": "#EF4444",   # Red
    "F": "#10B981",   # Green
    "Cl": "#22C55E",  # Green
    "Br": "#B91C1C",  # Dark red
    "I": "#7C3AED",   # Purple
    "S": "#F59E0B",   # Amber / yellow
    "P": "#EA580C",   # Orange
}


class AtomMobject(VGroup):
    """Visual representation of a chemical atom."""

    def __init__(
        self,
        symbol: str = "C",
        radius: float = 0.32,
        color: Optional[Union[str, ManimColor]] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.symbol = symbol

        atom_color = color or CPK_COLORS.get(symbol, t.primary)
        self.circle = Circle(
            radius=radius,
            fill_color=atom_color,
            fill_opacity=0.9,
            stroke_color=t.border,
            stroke_width=2.0,
        )
        self.label = Text(
            symbol,
            font_size=int(radius * 50),
            color="#FFFFFF" if symbol != "H" else "#000000",
            font=t.fonts.text_font,
            weight="BOLD",
        ).move_to(self.circle.get_center())

        self.add(self.circle, self.label)

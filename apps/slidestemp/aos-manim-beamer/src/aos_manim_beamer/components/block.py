from __future__ import annotations

from typing import Optional, Union
from manim import (
    VGroup,
    RoundedRectangle,
    Text,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
)
from manim.utils.color import ManimColor
from aos_manim_core import get_theme, ThemeConfig


class Block(VGroup):
    """Standard LaTeX Beamer-style block with header title bar and body."""

    def __init__(
        self,
        title: str,
        body_text: Optional[str] = None,
        width: float = 7.5,
        body_height: float = 1.6,
        header_color: Optional[Union[str, ManimColor]] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme

        h_color = header_color or t.primary
        header_h = 0.55

        # Header bar
        self.header_bg = RoundedRectangle(
            corner_radius=0.1,
            width=width,
            height=header_h,
            fill_color=h_color,
            fill_opacity=1.0,
            stroke_color=h_color,
            stroke_width=1.0,
        )
        self.header_label = Text(
            title,
            font_size=t.fonts.body_font_size - 4,
            color="#FFFFFF",
            font=t.fonts.text_font,
            weight="BOLD",
        ).move_to(self.header_bg.get_center())
        self.header = VGroup(self.header_bg, self.header_label)
        self.add(self.header)

        # Body container
        self.body_bg = RoundedRectangle(
            corner_radius=0.1,
            width=width,
            height=body_height,
            fill_color=t.surface,
            fill_opacity=0.95,
            stroke_color=h_color,
            stroke_width=1.5,
        )
        self.body_bg.next_to(self.header_bg, DOWN, buff=0)
        self.add(self.body_bg)

        # Optional body text
        if body_text:
            self.body_label = Text(
                body_text,
                font_size=t.fonts.body_font_size - 6,
                color=t.text_main,
                font=t.fonts.text_font,
            ).move_to(self.body_bg.get_center())
            self.add(self.body_label)


class AlertBlock(Block):
    """LaTeX Beamer Alert Block with warning / error styling."""

    def __init__(self, title: str, body_text: Optional[str] = None, theme: Optional[ThemeConfig] = None, **kwargs) -> None:
        current_theme = theme or get_theme()
        super().__init__(
            title=title,
            body_text=body_text,
            header_color=current_theme.error,
            theme=current_theme,
            **kwargs,
        )


class ExampleBlock(Block):
    """LaTeX Beamer Example Block with success / green styling."""

    def __init__(self, title: str, body_text: Optional[str] = None, theme: Optional[ThemeConfig] = None, **kwargs) -> None:
        current_theme = theme or get_theme()
        super().__init__(
            title=title,
            body_text=body_text,
            header_color=current_theme.success,
            theme=current_theme,
            **kwargs,
        )

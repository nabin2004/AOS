from __future__ import annotations

from typing import Optional, Union
from manim import (
    VGroup,
    RoundedRectangle,
    Rectangle,
    Text,
    Line,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
)
from aos_manim_core import get_theme, ThemeConfig
from aos_manim_slides import Slide


class BeamerFrame(Slide):
    """LaTeX Beamer Frame container with top banner and footline."""

    def __init__(
        self,
        title: str,
        subtitle: Optional[str] = None,
        section: Optional[str] = None,
        frame_number: Optional[int] = None,
        total_frames: Optional[int] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(title=None, subtitle=None, theme=theme, footer_text=None, **kwargs)
        t = self.theme

        # Top frametitle header banner
        banner_h = 0.95
        self.frametitle_bg = Rectangle(
            width=self.width,
            height=banner_h,
            fill_color=t.surface_variant,
            fill_opacity=1.0,
            stroke_color=t.border,
            stroke_width=1.0,
        )
        self.frametitle_bg.move_to(self.bg_frame.get_top() + DOWN * (banner_h / 2))
        self.add(self.frametitle_bg)

        # Title text
        self.title_text = Text(
            title,
            font_size=t.fonts.title_font_size - 10,
            color=t.text_main,
            font=t.fonts.text_font,
            weight="BOLD",
        )
        self.title_text.move_to(self.frametitle_bg.get_left() + RIGHT * (self.title_text.width / 2 + 0.4))
        self.add(self.title_text)

        if subtitle:
            self.sub_text = Text(
                subtitle,
                font_size=t.fonts.caption_font_size + 1,
                color=t.text_muted,
                font=t.fonts.text_font,
            )
            self.sub_text.next_to(self.title_text, RIGHT, buff=0.3)
            self.add(self.sub_text)

        # Bottom footline bar
        foot_h = 0.45
        self.footline_bg = Rectangle(
            width=self.width,
            height=foot_h,
            fill_color=t.surface_variant,
            fill_opacity=1.0,
            stroke_color=t.border,
            stroke_width=1.0,
        )
        self.footline_bg.move_to(self.bg_frame.get_bottom() + UP * (foot_h / 2))
        self.add(self.footline_bg)

        if section:
            sec_text = Text(
                section,
                font_size=t.fonts.caption_font_size - 1,
                color=t.text_muted,
                font=t.fonts.text_font,
            )
            sec_text.move_to(self.footline_bg.get_left() + RIGHT * (sec_text.width / 2 + 0.4))
            self.add(sec_text)

        if frame_number is not None:
            num_str = f"{frame_number}" if total_frames is None else f"{frame_number} / {total_frames}"
            num_text = Text(
                num_str,
                font_size=t.fonts.caption_font_size - 1,
                color=t.text_muted,
                font=t.fonts.text_font,
            )
            num_text.move_to(self.footline_bg.get_right() + LEFT * (num_text.width / 2 + 0.4))
            self.add(num_text)

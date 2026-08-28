from __future__ import annotations

from typing import Optional, Union
from manim import (
    VGroup,
    RoundedRectangle,
    Rectangle as ManimRectangle,
    Line,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
    config,
)
from manim.utils.color import ManimColor
from aos_manim_core import get_theme, ThemeConfig

from ..typography import slide_tex


class Card(VGroup):
    """Modern container card with customizable fill, border, and padding."""

    def __init__(
        self,
        width: float = 6.0,
        height: float = 4.0,
        corner_radius: Optional[float] = None,
        fill_color: Optional[Union[str, ManimColor]] = None,
        stroke_color: Optional[Union[str, ManimColor]] = None,
        fill_opacity: float = 0.85,
        stroke_width: Optional[float] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        current_theme = theme or get_theme()

        radius = corner_radius if corner_radius is not None else current_theme.corner_radius
        bg_color = fill_color or current_theme.surface
        b_color = stroke_color or current_theme.border
        s_width = stroke_width if stroke_width is not None else current_theme.default_stroke_width

        self.background_rect = RoundedRectangle(
            corner_radius=radius,
            width=width,
            height=height,
            fill_color=bg_color,
            fill_opacity=fill_opacity,
            stroke_color=b_color,
            stroke_width=s_width,
        )
        self.add(self.background_rect)


class Badge(VGroup):
    """Pill badge for tags, categories, or status indicators."""

    def __init__(
        self,
        text: str,
        color: Optional[Union[str, ManimColor]] = None,
        text_color: Optional[Union[str, ManimColor]] = None,
        font_size: int = 16,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        current_theme = theme or get_theme()
        badge_color = color or current_theme.primary
        txt_color = text_color or current_theme.text_main

        label = slide_tex(text, font_size=font_size, color=txt_color)
        bg = RoundedRectangle(
            corner_radius=0.15,
            width=label.width + 0.35,
            height=label.height + 0.2,
            fill_color=badge_color,
            fill_opacity=0.3,
            stroke_color=badge_color,
            stroke_width=1.5,
        )
        self.add(bg, label)


class CalloutBox(VGroup):
    """Highlighted note/warning/callout card with a prominent left accent bar."""

    def __init__(
        self,
        title: str,
        body: str,
        width: float = 6.5,
        height: float = 2.0,
        accent_color: Optional[Union[str, ManimColor]] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        current_theme = theme or get_theme()
        acc = accent_color or current_theme.accent

        card = Card(
            width=width,
            height=height,
            fill_color=current_theme.surface,
            stroke_color=current_theme.border,
            stroke_width=1.0,
            theme=current_theme,
        )
        accent_bar = Line(
            start=card.background_rect.get_corner(UP + LEFT),
            end=card.background_rect.get_corner(DOWN + LEFT),
            color=acc,
            stroke_width=5.0,
        )
        title_mob = slide_tex(
            title,
            font_size=current_theme.fonts.body_font_size,
            color=acc,
            weight="BOLD",
        ).next_to(card.background_rect.get_corner(UP + LEFT) + RIGHT * 0.3 + DOWN * 0.3, RIGHT, buff=0)

        body_mob = slide_tex(
            body,
            font_size=current_theme.fonts.caption_font_size + 2,
            color=current_theme.text_muted,
        ).next_to(title_mob, DOWN, aligned_edge=LEFT, buff=0.15)

        self.add(card, accent_bar, title_mob, body_mob)


class Rectangle(ManimRectangle):
    """Modern rectangle component with optional drawing animation and theme support."""

    def __init__(
        self,
        width: float = 2.0,
        height: float = 1.0,
        draw: bool = True,
        stroke_color: Optional[Union[str, ManimColor]] = None,
        fill_color: Optional[Union[str, ManimColor]] = None,
        fill_opacity: float = 0.0,
        stroke_width: Optional[float] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        self.draw = draw
        current_theme = theme or get_theme()
        s_color = stroke_color or current_theme.border
        f_color = fill_color or current_theme.surface
        s_width = stroke_width if stroke_width is not None else current_theme.default_stroke_width
        super().__init__(
            width=width,
            height=height,
            stroke_color=s_color,
            fill_color=f_color,
            fill_opacity=fill_opacity,
            stroke_width=s_width,
            **kwargs,
        )

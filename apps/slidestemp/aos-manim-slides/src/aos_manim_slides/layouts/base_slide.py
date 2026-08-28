from __future__ import annotations

from typing import Optional

from manim import (
    VGroup,
    Rectangle,
    RoundedRectangle,
    Line,
    config,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)

from aos_manim_core import get_theme, ThemeConfig

from ..document.markdown import parse_markdown, parse_slide_markdown
from ..document.model import Presentation, SlideSpec
from ..layout.box import Rect
from ..layout.engine import LayoutEngine
from ..layout.overflow import LayoutReport
from ..narration import assign_content_ids, collect_cue_index
from ..typography import slide_tex


class Slide(VGroup):
    """Base Slide container with header, content canvas, footer, and theme styling."""

    def __init__(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        slide_number: Optional[int] = None,
        total_slides: Optional[int] = None,
        footer_text: Optional[str] = "AOS Manim",
        theme: Optional[ThemeConfig] = None,
        show_background: bool = True,
        spec: Optional[SlideSpec] = None,
        total_bookmark_for_this_slide: str = "",
        total_this_slide_bookmark: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        self.title_text = title
        self.subtitle_text = subtitle
        self.slide_number = slide_number
        self.total_slides = total_slides
        self.layout_report: Optional[LayoutReport] = None
        
        if spec is None:
            spec = SlideSpec(
                title=title,
                subtitle=subtitle,
                layout="title-content",
            )
        self.spec = spec

        if total_bookmark_for_this_slide:
            spec.total_bookmark_for_this_slide = total_bookmark_for_this_slide
        if total_this_slide_bookmark:
            spec.total_this_slide_bookmark = total_this_slide_bookmark

        if spec is not None:
            if spec.footer is not None:
                footer_text = spec.footer
            if spec.title and title is None and spec.layout not in ("title", "section", "full-screen"):
                title = spec.title
                self.title_text = title
            if spec.subtitle and subtitle is None and spec.layout not in ("title", "section"):
                subtitle = spec.subtitle
                self.subtitle_text = subtitle

        self.frame_width = config.frame_width - (self.theme.canvas_margin * 2)
        self.frame_height = config.frame_height - (self.theme.canvas_margin * 2)
        # Keep historical attributes used by validators and callers.
        self.width = self.frame_width
        self.height = self.frame_height

        if show_background:
            self.bg_frame = RoundedRectangle(
                corner_radius=self.theme.corner_radius,
                width=self.frame_width,
                height=self.frame_height,
                fill_color=self.theme.background,
                fill_opacity=1.0,
                stroke_color=self.theme.border,
                stroke_width=1.5,
            )
            self.add(self.bg_frame)
        else:
            self.bg_frame = Rectangle(
                width=self.frame_width,
                height=self.frame_height,
                fill_opacity=0,
                stroke_opacity=0,
            )
            self.add(self.bg_frame)

        self.header_group = VGroup()
        if title:
            self._build_header(title, subtitle)
        self.add(self.header_group)

        self.content_group = VGroup()
        self.add(self.content_group)

        self.footer_group = VGroup()
        if footer_text or slide_number is not None:
            self._build_footer(footer_text, slide_number, total_slides)
        self.add(self.footer_group)

        self.cue_index = {}
        self.cueables = {}

        if spec is not None:
            self.apply_spec(spec)

    def _build_header(self, title: str, subtitle: Optional[str]) -> None:
        self.title_mob = slide_tex(
            title,
            font_size=self.theme.fonts.title_font_size,
            color=self.theme.text_main,
            weight="BOLD",
        )
        max_title_w = self.frame_width - 1.2
        if self.title_mob.width > max_title_w:
            self.title_mob.scale_to_fit_width(max_title_w)
        self.title_mob.move_to(
            self.bg_frame.get_top()
            + DOWN * 0.6
            + LEFT * (self.frame_width / 2 - self.title_mob.width / 2 - 0.5)
        )
        self.header_group.add(self.title_mob)

        header_depth = 1.3
        if subtitle:
            self.subtitle_mob = slide_tex(
                subtitle,
                font_size=self.theme.fonts.body_font_size - 4,
                color=self.theme.text_muted,
            )
            if self.subtitle_mob.width > max_title_w:
                self.subtitle_mob.scale_to_fit_width(max_title_w)
            self.subtitle_mob.next_to(self.title_mob, DOWN, aligned_edge=LEFT, buff=0.1)
            self.header_group.add(self.subtitle_mob)
            header_depth = 1.55

        divider = Line(
            start=self.bg_frame.get_top() + DOWN * header_depth + LEFT * (self.frame_width / 2 - 0.5),
            end=self.bg_frame.get_top() + DOWN * header_depth + RIGHT * (self.frame_width / 2 - 0.5),
            color=self.theme.border,
            stroke_width=1.0,
        )
        self.header_group.add(divider)
        self._header_depth = header_depth

    def _build_footer(
        self,
        footer_text: Optional[str],
        slide_number: Optional[int],
        total_slides: Optional[int],
    ) -> None:
        foot_line = Line(
            start=self.bg_frame.get_bottom() + UP * 0.6 + LEFT * (self.frame_width / 2 - 0.5),
            end=self.bg_frame.get_bottom() + UP * 0.6 + RIGHT * (self.frame_width / 2 - 0.5),
            color=self.theme.border,
            stroke_width=1.0,
        )
        self.footer_group.add(foot_line)

        if footer_text:
            foot_mob = slide_tex(
                footer_text,
                font_size=self.theme.fonts.caption_font_size,
                color=self.theme.text_muted,
            )
            foot_mob.move_to(
                self.bg_frame.get_bottom()
                + UP * 0.3
                + LEFT * (self.frame_width / 2 - foot_mob.width / 2 - 0.5)
            )
            self.footer_group.add(foot_mob)

        if slide_number is not None:
            num_str = f"{slide_number}" if total_slides is None else f"{slide_number} / {total_slides}"
            num_mob = slide_tex(
                num_str,
                font_size=self.theme.fonts.caption_font_size,
                color=self.theme.text_muted,
            )
            num_mob.move_to(
                self.bg_frame.get_bottom()
                + UP * 0.3
                + RIGHT * (self.frame_width / 2 - num_mob.width / 2 - 0.5)
            )
            self.footer_group.add(num_mob)

    def add_content(self, *mobjects) -> Slide:
        for mob in mobjects:
            self.content_group.add(mob)
        return self

    def get_content_center(self) -> list[float]:
        rect = self.get_content_rect()
        return rect.center

    def get_content_rect(self) -> Rect:
        """Measured content area: frame minus chrome, header, and footer."""
        pad = 0.5
        left = self.bg_frame.get_left()[0] + pad
        right = self.bg_frame.get_right()[0] - pad
        header_depth = getattr(self, "_header_depth", 1.4 if len(self.header_group) > 0 else 0.45)
        top = self.bg_frame.get_top()[1] - (header_depth + 0.32 if len(self.header_group) > 0 else 0.5)
        bottom = self.bg_frame.get_bottom()[1] + (0.75 if len(self.footer_group) > 0 else 0.4)
        return Rect(left, bottom, max(right - left, 0.5), max(top - bottom, 0.5))

    def apply_spec(self, spec: SlideSpec, engine: Optional[LayoutEngine] = None) -> LayoutReport:
        self.spec = spec
        assign_content_ids(spec)
        engine = engine or LayoutEngine()
        self.content_group.remove(*list(self.content_group.submobjects))
        root, report, ctx = engine.layout_spec(spec, self.get_content_rect(), theme=self.theme)
        if root.mobject is not None:
            self.add_content(root.mobject)
        self.layout_report = report
        self.layout_root = root
        self.cue_index, self.cueables = collect_cue_index(root)
        if spec.layout in ("title", "section") and hasattr(self, "title_mob") is False:
            pass
        elif hasattr(self, "title_mob") and ctx.title_font_size < self.theme.fonts.title_font_size:
            scale = ctx.title_font_size / max(self.theme.fonts.title_font_size, 1)
            self.title_mob.scale(scale)
        return report

    @classmethod
    def from_spec(cls, spec: SlideSpec, theme: Optional[ThemeConfig] = None, **kwargs) -> Slide:
        headerless = spec.layout in ("title", "section", "full-screen")
        return cls(
            title=None if headerless else spec.title,
            subtitle=None if headerless else spec.subtitle,
            footer_text=spec.footer if spec.footer is not None else kwargs.pop("footer_text", "AOS Manim"),
            theme=theme,
            spec=spec,
            **kwargs,
        )

    @classmethod
    def from_markdown(cls, markdown: str, theme: Optional[ThemeConfig] = None, **kwargs) -> Slide:
        spec = parse_slide_markdown(markdown)
        return cls.from_spec(spec, theme=theme, **kwargs)

    @classmethod
    def deck_from_markdown(cls, markdown: str, theme: Optional[ThemeConfig] = None, **kwargs) -> list[Slide]:
        presentation = parse_markdown(markdown)
        total = len(presentation.slides)
        slides = []
        for i, spec in enumerate(presentation.slides, start=1):
            if spec.footer is None and presentation.footer:
                spec.footer = presentation.footer
            slides.append(
                cls.from_spec(spec, theme=theme, slide_number=i, total_slides=total, **kwargs)
            )
        return slides

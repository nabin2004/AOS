from __future__ import annotations

from typing import List, Optional, Union

from manim import VGroup

from aos_manim_core import ThemeConfig

from ..document.model import Callout, ListBlock, RawMobject, SlideSpec
from .base_slide import Slide


class TitleSlide(Slide):
    """Hero title slide with presentation title, subtitle, author, and date."""

    def __init__(
        self,
        title: str,
        subtitle: Optional[str] = None,
        author: Optional[str] = None,
        date: Optional[str] = None,
        affiliation: Optional[str] = None,
        theme: Optional[ThemeConfig] = None,
        bookmark_per_slide: Optional[str] = None,
        total_bookmark_for_this_slide: str = "",
        total_this_slide_bookmark: str = "",
        **kwargs,
    ) -> None:
        spec = SlideSpec(
            title=title,
            subtitle=subtitle,
            layout="title",
            author=author,
            date=date,
            affiliation=affiliation,
            bookmark_per_slide=bookmark_per_slide,
            total_bookmark_for_this_slide=total_bookmark_for_this_slide,
            total_this_slide_bookmark=total_this_slide_bookmark,
        )
        super().__init__(title=None, subtitle=None, theme=theme, footer_text=None, spec=spec, total_bookmark_for_this_slide=total_bookmark_for_this_slide, total_this_slide_bookmark=total_this_slide_bookmark, **kwargs)


class SectionSlide(Slide):
    """Section divider slide with section number and title."""

    def __init__(
        self,
        section_title: str,
        section_number: Optional[Union[int, str]] = None,
        subtitle: Optional[str] = None,
        theme: Optional[ThemeConfig] = None,
        total_bookmark_for_this_slide: str = "",
        total_this_slide_bookmark: str = "",
        **kwargs,
    ) -> None:
        spec = SlideSpec(
            title=section_title,
            subtitle=subtitle,
            layout="section",
            section_number=section_number,
            total_bookmark_for_this_slide=total_bookmark_for_this_slide,
            total_this_slide_bookmark=total_this_slide_bookmark,
        )
        super().__init__(title=None, subtitle=None, theme=theme, spec=spec, total_bookmark_for_this_slide=total_bookmark_for_this_slide, total_this_slide_bookmark=total_this_slide_bookmark, **kwargs)


class ContentSlide(Slide):
    """Standard presentation slide with bullet points and optional callout."""

    def __init__(
        self,
        title: str,
        bullets: List[str],
        callout: Optional[tuple[str, str]] = None,
        subtitle: Optional[str] = None,
        theme: Optional[ThemeConfig] = None,
        total_bookmark_for_this_slide: str = "",
        total_this_slide_bookmark: str = "",
        **kwargs,
    ) -> None:
        blocks: list = [ListBlock(items=list(bullets))]
        if callout:
            blocks.append(Callout(title=callout[0], body=callout[1], role="decoration"))
        spec = SlideSpec(
            title=title,
            subtitle=subtitle,
            layout="title-content",
            blocks=blocks,
            total_bookmark_for_this_slide=total_bookmark_for_this_slide,
            total_this_slide_bookmark=total_this_slide_bookmark,
        )
        super().__init__(title=title, subtitle=subtitle, theme=theme, spec=spec, total_bookmark_for_this_slide=total_bookmark_for_this_slide, total_this_slide_bookmark=total_this_slide_bookmark, **kwargs)


class TwoColumnSlide(Slide):
    """Two column slide layout with custom left and right content."""

    def __init__(
        self,
        title: str,
        left_content: VGroup,
        right_content: VGroup,
        col_width: float = 5.2,
        subtitle: Optional[str] = None,
        theme: Optional[ThemeConfig] = None,
        total_bookmark_for_this_slide: str = "",
        total_this_slide_bookmark: str = "",
        **kwargs,
    ) -> None:
        spec = SlideSpec(
            title=title,
            subtitle=subtitle,
            layout="two-column",
            left=[RawMobject(mobject=left_content)],
            right=[RawMobject(mobject=right_content)],
            ratios=[0.5, 0.5],
            total_bookmark_for_this_slide=total_bookmark_for_this_slide,
            total_this_slide_bookmark=total_this_slide_bookmark,
        )
        super().__init__(title=title, subtitle=subtitle, theme=theme, spec=spec, total_bookmark_for_this_slide=total_bookmark_for_this_slide, total_this_slide_bookmark=total_this_slide_bookmark, **kwargs)


class QuizSlide(Slide):
    """Interactive quiz/question slide with selectable multiple choices."""

    def __init__(
        self,
        question: str,
        options: List[str],
        correct_index: int = 0,
        explanation: Optional[str] = None,
        title: str = "Knowledge Check",
        theme: Optional[ThemeConfig] = None,
        total_bookmark_for_this_slide: str = "",
        total_this_slide_bookmark: str = "",
        **kwargs,
    ) -> None:
        spec = SlideSpec(
            title=title,
            layout="quiz",
            question=question,
            options=list(options),
            correct_index=correct_index,
            explanation=explanation,
            total_bookmark_for_this_slide=total_bookmark_for_this_slide,
            total_this_slide_bookmark=total_this_slide_bookmark,
        )
        super().__init__(title=title, theme=theme, spec=spec, total_bookmark_for_this_slide=total_bookmark_for_this_slide, total_this_slide_bookmark=total_this_slide_bookmark, **kwargs)
        self.correct_index = correct_index
        self.option_cards = []

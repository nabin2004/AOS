from __future__ import annotations

from manim import config

from aos_manim_core import ThemeConfig, get_theme

from ..document.model import SlideSpec
from .box import LayoutContext, Rect
from .overflow import OverflowSolver
from .recipes import WIDE_ASPECT as RECIPE_WIDE_ASPECT


class LayoutEngine:
    """Deterministic layout: maps a SlideSpec into positioned Manim mobjects."""

    def __init__(self, solver: OverflowSolver | None = None) -> None:
        self.solver = solver or OverflowSolver()

    def context_from_theme(
        self,
        theme: ThemeConfig | None = None,
        *,
        aspect_ratio: float | None = None,
        collapse_columns: bool | None = None,
    ) -> LayoutContext:
        t = theme or get_theme()
        aspect = aspect_ratio if aspect_ratio is not None else (config.frame_width / max(config.frame_height, 0.01))
        ctx = LayoutContext(
            body_font_size=t.fonts.body_font_size,
            title_font_size=t.fonts.title_font_size,
            heading_font_size=t.fonts.heading_font_size,
            equation_font_size=max(t.fonts.heading_font_size + 8, 36),
            code_font_size=t.fonts.code_font_size,
            caption_font_size=t.fonts.caption_font_size,
            aspect_ratio=aspect,
            theme=t,
        )
        if collapse_columns is None:
            ctx.collapse_columns = aspect < RECIPE_WIDE_ASPECT
        else:
            ctx.collapse_columns = collapse_columns
        return ctx

    def layout_spec(
        self,
        spec: SlideSpec,
        content_rect: Rect,
        theme: ThemeConfig | None = None,
        *,
        aspect_ratio: float | None = None,
    ) -> tuple:
        aspect = aspect_ratio if aspect_ratio is not None else spec.aspect
        ctx = self.context_from_theme(theme, aspect_ratio=aspect)
        root, report = self.solver.fit(spec, ctx, content_rect)
        return root, report, ctx

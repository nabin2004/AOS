from __future__ import annotations

from typing import Optional, List, Union
from manim import (
    VGroup,
    RoundedRectangle,
    Rectangle,
    Dot,
    Text,
    Line,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
)
from aos_manim_core import get_theme, ThemeConfig, Cue, CueAction, apply_standard_cue


class CodeWindow(VGroup):
    """Modern code editor window with title bar, window controls, and line highlighting."""

    def __init__(
        self,
        code: str,
        filename: str = "solution.py",
        width: float = 7.0,
        height: float = 4.5,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.width = width
        self.height = height

        # Window background frame
        self.frame = RoundedRectangle(
            corner_radius=0.18,
            width=width,
            height=height,
            fill_color=t.surface,
            fill_opacity=1.0,
            stroke_color=t.border,
            stroke_width=2.0,
        )
        self.add(self.frame)

        # Title bar
        title_bar_height = 0.55
        self.title_bar = RoundedRectangle(
            corner_radius=0.18,
            width=width,
            height=title_bar_height,
            fill_color=t.surface_variant,
            fill_opacity=1.0,
            stroke_color=t.border,
            stroke_width=1.0,
        )
        self.title_bar.move_to(self.frame.get_top() + DOWN * (title_bar_height / 2))

        # Mac-style dots
        dot_r = 0.07
        dot_close = Dot(radius=dot_r, color=t.error)
        dot_min = Dot(radius=dot_r, color=t.warning)
        dot_max = Dot(radius=dot_r, color=t.success)
        dots = VGroup(dot_close, dot_min, dot_max).arrange(RIGHT, buff=0.12)
        dots.move_to(self.title_bar.get_left() + RIGHT * 0.45)

        # Filename
        title_text = Text(
            filename,
            font_size=15,
            color=t.text_muted,
            font=t.fonts.code_font,
        ).move_to(self.title_bar.get_center())

        self.add(self.title_bar, dots, title_text)

        # Code lines
        self.code_lines = code.strip().split("\n")
        self.line_mobs = VGroup()

        for i, line_str in enumerate(self.code_lines):
            num_txt = Text(
                f"{i+1:2d}",
                font_size=t.fonts.code_font_size - 4,
                color=t.text_muted,
                font=t.fonts.code_font,
            )
            code_txt = Text(
                line_str,
                font_size=t.fonts.code_font_size - 3,
                color=t.text_main,
                font=t.fonts.code_font,
            )
            row = VGroup(num_txt, code_txt).arrange(RIGHT, buff=0.25)
            self.line_mobs.add(row)

        self.line_mobs.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        self.line_mobs.next_to(self.title_bar, DOWN, buff=0.3, aligned_edge=LEFT)
        self.line_mobs.shift(RIGHT * 0.4)
        self.add(self.line_mobs)

        # Active line indicator (hidden by default)
        self.highlight_bar = Rectangle(
            width=width - 0.2,
            height=0.35,
            fill_color=t.primary,
            fill_opacity=0.25,
            stroke_color=t.primary,
            stroke_width=1.0,
        )
        self.highlight_bar.set_opacity(0)
        self.add(self.highlight_bar)

    def highlight_line(self, line_num: int) -> None:
        """Positions highlight bar over 1-indexed line number."""
        idx = line_num - 1
        if 0 <= idx < len(self.line_mobs):
            target_line = self.line_mobs[idx]
            self.highlight_bar.move_to(target_line.get_center())
            self.highlight_bar.set_opacity(0.3)

    def cue_targets(self) -> dict:
        return {"base": self, "bar": self.highlight_bar}

    def step_count(self) -> int:
        return len(self.code_lines)

    def apply_cue(self, scene, cue: Cue) -> None:
        if cue.action == CueAction.REVEAL:
            apply_standard_cue(scene, cue, self, theme=self.theme)
            return
        if cue.action in (CueAction.STEP, CueAction.HIGHLIGHT):
            payload = cue.payload or {}
            if "line" in payload:
                line = int(payload["line"])
            else:
                line = int(payload.get("i", 0)) + 1
            self.highlight_line(line)
            return
        apply_standard_cue(scene, cue, self, theme=self.theme)

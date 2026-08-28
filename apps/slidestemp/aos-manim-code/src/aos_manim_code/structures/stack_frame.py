from __future__ import annotations

from typing import Optional, Dict, Any, List
from manim import (
    VGroup,
    RoundedRectangle,
    Text,
    Line,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
)
from aos_manim_core import get_theme, ThemeConfig


class StackFrameMobject(VGroup):
    """Visualizes an individual function call stack frame with local variables."""

    def __init__(
        self,
        func_name: str,
        local_vars: Dict[str, Any],
        width: float = 4.2,
        height: float = 1.6,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.func_name = func_name
        self.local_vars = local_vars

        self.box = RoundedRectangle(
            corner_radius=0.12,
            width=width,
            height=height,
            fill_color=t.surface,
            fill_opacity=1.0,
            stroke_color=t.secondary,
            stroke_width=2.0,
        )
        self.add(self.box)

        # Header with function name
        header_text = Text(
            f"{func_name}()",
            font_size=t.fonts.body_font_size - 4,
            color=t.secondary,
            font=t.fonts.code_font,
            weight="BOLD",
        ).move_to(self.box.get_top() + DOWN * 0.3)
        self.add(header_text)

        div = Line(
            self.box.get_top() + DOWN * 0.55 + LEFT * (width / 2 - 0.2),
            self.box.get_top() + DOWN * 0.55 + RIGHT * (width / 2 - 0.2),
            color=t.border,
            stroke_width=1.0,
        )
        self.add(div)

        # Local variables
        var_mobs = VGroup()
        for k, v in local_vars.items():
            txt = Text(
                f"{k} = {v}",
                font_size=t.fonts.code_font_size - 5,
                color=t.text_main,
                font=t.fonts.code_font,
            )
            var_mobs.add(txt)

        if len(var_mobs) > 0:
            var_mobs.arrange(DOWN, aligned_edge=LEFT, buff=0.1)
            var_mobs.next_to(div, DOWN, buff=0.2, aligned_edge=LEFT)
            var_mobs.shift(RIGHT * 0.4)
            self.add(var_mobs)


class CallStackMobject(VGroup):
    """Visualizes the runtime call stack growing upwards/downwards."""

    def __init__(
        self,
        title: str = "Call Stack",
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme

        self.title_mob = Text(
            title,
            font_size=t.fonts.heading_font_size - 6,
            color=t.text_main,
            font=t.fonts.text_font,
            weight="BOLD",
        )
        self.add(self.title_mob)

        self.frames_group = VGroup()
        self.add(self.frames_group)

    def push_frame(self, frame: StackFrameMobject) -> None:
        self.frames_group.add(frame)
        self.frames_group.arrange(UP, buff=0.25)
        self.title_mob.next_to(self.frames_group, UP, buff=0.4)

    def pop_frame(self) -> Optional[StackFrameMobject]:
        if len(self.frames_group) > 0:
            frame = self.frames_group[-1]
            self.frames_group.remove(frame)
            if len(self.frames_group) > 0:
                self.frames_group.arrange(UP, buff=0.25)
                self.title_mob.next_to(self.frames_group, UP, buff=0.4)
            return frame
        return None

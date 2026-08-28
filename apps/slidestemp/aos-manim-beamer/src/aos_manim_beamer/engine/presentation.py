from __future__ import annotations

from typing import Optional, List, Union
from aos_manim_core import get_theme, set_theme, ThemeConfig
from ..components.frame import BeamerFrame
from ..components.block import Block, AlertBlock, ExampleBlock


class BeamerPresentation:
    """Orchestration engine for LaTeX Beamer-style presentations."""

    def __init__(
        self,
        title: str = "Presentation",
        theme: Optional[Union[str, ThemeConfig]] = None,
    ) -> None:
        self.title = title
        if theme:
            set_theme(theme)
        self.theme = get_theme()
        self.frames: List[BeamerFrame] = []

    def frame(
        self,
        title: str,
        subtitle: Optional[str] = None,
        section: Optional[str] = None,
    ) -> BeamerFrame:
        """Create and register a new BeamerFrame."""
        f_num = len(self.frames) + 1
        frame = BeamerFrame(
            title=title,
            subtitle=subtitle,
            section=section,
            frame_number=f_num,
            theme=self.theme,
        )
        self.frames.append(frame)
        return frame

    def __len__(self) -> int:
        return len(self.frames)

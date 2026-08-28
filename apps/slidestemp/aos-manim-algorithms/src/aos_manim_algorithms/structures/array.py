from __future__ import annotations

from typing import Optional, List, Union, Dict, Any
from manim import (
    VGroup,
    RoundedRectangle,
    Text,
    Arrow,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
)
from manim.utils.color import ManimColor
from aos_manim_core import get_theme, ThemeConfig


class ArrayCell(VGroup):
    """A single cell in an ArrayMobject."""

    def __init__(
        self,
        value: Any,
        index: int,
        cell_size: float = 0.9,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        self.value = value
        self.index = index
        self.cell_size = cell_size

        t = self.theme
        self.rect = RoundedRectangle(
            corner_radius=0.1,
            width=cell_size,
            height=cell_size,
            fill_color=t.surface,
            fill_opacity=1.0,
            stroke_color=t.border,
            stroke_width=2.0,
        )
        self.val_text = Text(
            str(value),
            font_size=t.fonts.body_font_size - 2,
            color=t.text_main,
            font=t.fonts.text_font,
            weight="BOLD",
        ).move_to(self.rect.get_center())

        self.idx_text = Text(
            str(index),
            font_size=t.fonts.caption_font_size,
            color=t.text_muted,
            font=t.fonts.text_font,
        ).next_to(self.rect, DOWN, buff=0.15)

        self.add(self.rect, self.val_text, self.idx_text)

    def set_highlight(self, color: Union[str, ManimColor], fill_opacity: float = 0.4) -> None:
        self.rect.set_stroke(color=color, width=3.5)
        self.rect.set_fill(color=color, opacity=fill_opacity)

    def reset_style(self) -> None:
        t = self.theme
        self.rect.set_stroke(color=t.border, width=2.0)
        self.rect.set_fill(color=t.surface, opacity=1.0)


class ArrayMobject(VGroup):
    """Interactive array visualizer with cell highlighting and pointers."""

    def __init__(
        self,
        values: List[Any],
        cell_size: float = 0.9,
        buff: float = 0.15,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        self.cells: List[ArrayCell] = []

        for i, val in enumerate(values):
            cell = ArrayCell(val, index=i, cell_size=cell_size, theme=self.theme)
            self.cells.append(cell)
            self.add(cell)

        self.arrange(RIGHT, buff=buff)

    def get_cell(self, index: int) -> ArrayCell:
        if 0 <= index < len(self.cells):
            return self.cells[index]
        raise IndexError(f"Index {index} out of bounds for array of size {len(self.cells)}")

    def highlight_index(self, index: int, color: Optional[Union[str, ManimColor]] = None) -> None:
        c = color or self.theme.accent
        self.get_cell(index).set_highlight(c)

    def reset_all(self) -> None:
        for cell in self.cells:
            cell.reset_style()

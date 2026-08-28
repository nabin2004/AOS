from __future__ import annotations

from typing import Optional, Union
import numpy as np
from manim import (
    VGroup,
    Line,
)
from manim.utils.color import ManimColor
# pyrefly: ignore [missing-import]
from aos_manim_core import get_theme, ThemeConfig


class BondMobject(VGroup):
    """Visual representation of a chemical bond (single, double, triple)."""

    def __init__(
        self,
        start_point: list[float] | np.ndarray,
        end_point: list[float] | np.ndarray,
        order: int = 1,
        color: Optional[Union[str, ManimColor]] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        bond_color = color or t.border

        p1 = np.array(start_point, dtype=float)
        p2 = np.array(end_point, dtype=float)
        diff = p2 - p1
        length = np.linalg.norm(diff)

        if length < 1e-6:
            return

        unit = diff / length
        # Normal vector in xy plane
        normal = np.array([-unit[1], unit[0], 0.0])

        if order == 1:
            line = Line(p1, p2, color=bond_color, stroke_width=3.5)
            self.add(line)
        elif order == 2:
            offset = 0.08
            l1 = Line(p1 + normal * offset, p2 + normal * offset, color=bond_color, stroke_width=2.5)
            l2 = Line(p1 - normal * offset, p2 - normal * offset, color=bond_color, stroke_width=2.5)
            self.add(l1, l2)
        elif order == 3:
            offset = 0.12
            l1 = Line(p1 + normal * offset, p2 + normal * offset, color=bond_color, stroke_width=2.0)
            l2 = Line(p1, p2, color=bond_color, stroke_width=2.0)
            l3 = Line(p1 - normal * offset, p2 - normal * offset, color=bond_color, stroke_width=2.0)
            self.add(l1, l2, l3)

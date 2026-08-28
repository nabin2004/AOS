from __future__ import annotations

from typing import Optional, Dict, Any, List
import numpy as np
from manim import (
    VGroup,
    Square,
    RoundedRectangle,
    Arrow,
    MathTex,
    Text,
    ORIGIN,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig


class FreeBodyDiagram(VGroup):
    """Free body diagram representing forces acting on a body."""

    def __init__(
        self,
        mass: float = 1.0,
        forces: Optional[Dict[str, tuple[float, float]]] = None,
        block_size: float = 1.2,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.mass = mass

        # Default forces: (Fx, Fy)
        # e.g. {"F_g": (0, -9.81), "F_N": (0, 9.81), "F_app": (5.0, 0), "F_f": (-2.0, 0)}
        self.forces = forces or {
            "F_g": (0.0, -2.0),
            "F_N": (0.0, 2.0),
            "F_{app}": (2.5, 0.0),
            "F_f": (-1.0, 0.0),
        }

        # Center body
        self.body = RoundedRectangle(
            corner_radius=0.1,
            width=block_size,
            height=block_size,
            fill_color=t.surface,
            fill_opacity=1.0,
            stroke_color=t.primary,
            stroke_width=2.5,
        )
        self.mass_label = MathTex(rf"m = {mass} \, \text{{kg}}", font_size=18, color=t.text_main)
        self.mass_label.move_to(self.body.get_center())
        self.add(self.body, self.mass_label)

        # Force arrows
        scale = 0.6
        self.arrows_group = VGroup()
        for name, (fx, fy) in self.forces.items():
            start = self.body.get_center()
            end = start + np.array([fx * scale, fy * scale, 0.0])
            arr = Arrow(start, end, buff=0, color=t.accent, stroke_width=3.5)
            lbl = MathTex(rf"\vec{{{name}}}", font_size=20, color=t.accent)
            lbl.next_to(end, np.array([np.sign(fx), np.sign(fy), 0.0]), buff=0.15)
            self.arrows_group.add(arr, lbl)

        self.add(self.arrows_group)

    def compute_net_force(self) -> tuple[float, float]:
        net_x = sum(fx for fx, _ in self.forces.values())
        net_y = sum(fy for _, fy in self.forces.values())
        return (net_x, net_y)

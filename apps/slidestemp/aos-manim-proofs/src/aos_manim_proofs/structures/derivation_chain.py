from __future__ import annotations

from typing import Optional, List
from manim import (
    VGroup,
    RoundedRectangle,
    MathTex,
    Text,
    Line,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
)
from aos_manim_core import get_theme, ThemeConfig
from .proof_step import ProofStep, StepType


class DerivationChain(VGroup):
    """Step-by-step mathematical derivation card."""

    def __init__(
        self,
        theorem: str,
        steps: List[ProofStep],
        width: float = 8.5,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme

        # Theorem banner
        thm_box = RoundedRectangle(
            corner_radius=0.12,
            width=width,
            height=1.0,
            fill_color=t.surface_variant,
            fill_opacity=1.0,
            stroke_color=t.primary,
            stroke_width=2.0,
        )
        thm_label = Text("Theorem:", font_size=18, color=t.primary, font=t.fonts.text_font, weight="BOLD")
        thm_text = MathTex(theorem, font_size=22, color=t.text_main)
        thm_group = VGroup(thm_label, thm_text).arrange(RIGHT, buff=0.3).move_to(thm_box.get_center())

        header = VGroup(thm_box, thm_group)
        self.add(header)

        # Step rows
        step_mobs = VGroup()
        for i, s in enumerate(steps):
            # Step card
            card = RoundedRectangle(
                corner_radius=0.1,
                width=width,
                height=0.85,
                fill_color=t.surface,
                fill_opacity=0.9,
                stroke_color=t.border if s.step_type != StepType.QED else t.success,
                stroke_width=1.5 if s.step_type != StepType.QED else 2.5,
            )
            step_num = Text(f"{i+1}.", font_size=16, color=t.accent, font=t.fonts.text_font, weight="BOLD")
            stmt = MathTex(s.statement, font_size=20, color=t.text_main)
            just = Text(f"({s.justification})", font_size=14, color=t.text_muted, font=t.fonts.text_font)

            step_num.move_to(card.get_left() + RIGHT * 0.4)
            stmt.next_to(step_num, RIGHT, buff=0.3)
            just.move_to(card.get_right() + LEFT * (just.width / 2 + 0.3))

            row = VGroup(card, step_num, stmt, just)
            step_mobs.add(row)

        step_mobs.arrange(DOWN, buff=0.18)
        step_mobs.next_to(header, DOWN, buff=0.3)
        self.add(step_mobs)

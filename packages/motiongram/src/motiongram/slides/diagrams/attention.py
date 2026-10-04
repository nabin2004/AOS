"""Attention diagram component for transformer tokens and attention weights."""

from __future__ import annotations

from typing import Any

from manim import Arrow, RoundedRectangle, Text, VGroup

from motiongram.slides.diagrams.base import SlideDiagram


class AttentionDiagram(SlideDiagram):
    """Transformer attention flow showing tokens and weighted attention arrows."""

    def __init__(
        self,
        tokens: list[str],
        target_token: str | None = None,
        weights: list[dict[str, Any]] | None = None,
        token_color: str = "#58C4DD",
        target_color: str = "#FFFF00",
        arrow_color: str = "#83C167",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        token_mobs: dict[str, VGroup] = {}
        ordered_mobs: list[VGroup] = []

        # 1. Create token boxes
        for tok in tokens:
            is_target = (tok == target_token)
            color = target_color if is_target else token_color

            lbl = Text(tok, font_size=28, color="#FFFFFF")
            box = RoundedRectangle(
                corner_radius=0.15,
                width=max(lbl.width + 0.6, 1.4),
                height=max(lbl.height + 0.5, 0.8),
                color=color,
                fill_color="#222222",
                fill_opacity=0.8,
            )
            tok_grp = VGroup(box, lbl)
            token_mobs[tok] = tok_grp
            ordered_mobs.append(tok_grp)

            self.register_selector(f"token[{tok}]", tok_grp)
            self.register_selector(f"box[{tok}]", box)
            self.register_selector(f"text[{tok}]", lbl)

        tokens_row = VGroup(*ordered_mobs).arrange(direction=[1, 0, 0], buff=0.8)
        self.add(tokens_row)

        # 2. Draw attention connections if specified
        if weights:
            for w_entry in weights:
                src = w_entry.get("from")
                tgt = w_entry.get("to")
                weight = float(w_entry.get("weight", 0.5))
                if src in token_mobs and tgt in token_mobs:
                    m_src = token_mobs[src]
                    m_tgt = token_mobs[tgt]
                    # Arrow over the top
                    arr = Arrow(
                        m_src.get_top(),
                        m_tgt.get_top(),
                        color=arrow_color,
                        stroke_width=max(1.5, weight * 6.0),
                        buff=0.15,
                    )
                    self.add(arr)
                    self.register_selector(f"arrow[{src}->{tgt}]", arr)

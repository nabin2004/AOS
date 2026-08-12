"""Attention visualizers (d2l Ch 11)."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, RIGHT, MathTex, Square, Text, VGroup, WHITE

from manim_ai.compute import attention as attn_ops
from manim_ai.compute import tensors as tensor_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME
from manim_ai.core.utils import matrix_grid


@register_concept(
    id="self_attention",
    domain="transformer",
    chapter="11.6",
    title="Self-Attention",
    tags=["attention", "transformer"],
)
def build_self_attention(tokens: Sequence[str] | None = None) -> VGroup:
    tokens = list(tokens or ["I", "love", "AI"])
    tokens, weights, _out = attn_ops.attention_from_tokens(tokens, dim=4, seed=0)
    tok_row = VGroup(*[Text(t, font_size=22, color=WHITE) for t in tokens]).arrange(RIGHT, buff=0.55)
    grid = matrix_grid(tensor_ops.round_grid(weights, decimals=2), cell=0.55)
    title = Text("Self-attention weights", font_size=26, color=WHITE)
    eq = MathTex(r"\mathrm{Attention}(Q,K,V)=\mathrm{softmax}\!\left(\frac{QK^\top}{\sqrt{d}}\right)V", font_size=26)
    return VGroup(title, tok_row, grid, eq).arrange(DOWN, buff=0.3)


@register_concept(
    id="qkv",
    domain="transformer",
    chapter="11.1",
    title="Queries, Keys, Values",
    tags=["attention"],
)
def build_qkv() -> VGroup:
    boxes = VGroup(
        *[
            VGroup(
                Square(1.0, color=c, fill_opacity=0.25),
                Text(lab, font_size=28, color=WHITE),
            )
            for lab, c in [("Q", DEFAULT_THEME.primary), ("K", DEFAULT_THEME.secondary), ("V", DEFAULT_THEME.attention)]
        ]
    ).arrange(RIGHT, buff=0.5)
    title = Text("Queries · Keys · Values", font_size=28, color=WHITE)
    return VGroup(title, boxes).arrange(DOWN, buff=0.4)


@register_concept(
    id="multi_head_attention",
    domain="transformer",
    chapter="11.5",
    title="Multi-Head Attention",
    tags=["attention"],
)
def build_multi_head_attention(heads: int = 4) -> VGroup:
    head_boxes = VGroup(
        *[
            VGroup(Square(0.7, color=DEFAULT_THEME.attention, fill_opacity=0.3), Text(f"H{i+1}", font_size=16))
            for i in range(heads)
        ]
    ).arrange(RIGHT, buff=0.2)
    title = Text("Multi-head attention", font_size=26, color=WHITE)
    note = MathTex(r"\mathrm{Concat}(h_1,\ldots,h_h)W^O", font_size=28)
    return VGroup(title, head_boxes, note).arrange(DOWN, buff=0.35)

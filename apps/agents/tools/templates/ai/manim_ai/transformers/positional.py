"""Positional encoding (d2l Ch 11.6.3)."""

from __future__ import annotations

from manim import DOWN, Axes, MathTex, Text, VGroup, WHITE

from manim_ai.compute import positional as pe_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


@register_concept(
    id="positional_encoding",
    domain="transformer",
    chapter="11.6.3",
    title="Positional Encoding",
    tags=["transformer"],
)
def build_positional_encoding() -> VGroup:
    pe = pe_ops.sinusoidal_pe(length=32, dim=16)
    axes = Axes(x_range=[0, 20, 5], y_range=[-1.2, 1.2, 1], x_length=6.5, y_length=3).scale(0.8)
    # Plot PE[:,0] and PE[:,1] (sin/cos pair at lowest frequency).
    sine = axes.plot(lambda x: float(pe[min(int(x), len(pe) - 1), 0]), color=DEFAULT_THEME.primary)
    cosine = axes.plot(lambda x: float(pe[min(int(x), len(pe) - 1), 1]), color=DEFAULT_THEME.secondary)
    title = Text("Positional encoding", font_size=26, color=WHITE)
    eq = MathTex(r"PE_{(pos,2i)}=\sin(pos/10000^{2i/d})", font_size=26)
    return VGroup(title, axes, sine, cosine, eq).arrange(DOWN, buff=0.2)

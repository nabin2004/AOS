"""RNN / LSTM cell diagrams (d2l Ch 9–10)."""

from __future__ import annotations

from manim import DOWN, LEFT, RIGHT, Circle, Line, MathTex, Rectangle, Text, VGroup, WHITE

from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


@register_concept(
    id="rnn_cell",
    domain="recurrent",
    chapter="9.4",
    title="RNN Cell",
    tags=["rnn"],
)
def build_rnn_cell() -> VGroup:
    box = Rectangle(width=2.2, height=1.2, color=DEFAULT_THEME.primary, fill_opacity=0.25)
    lab = Text("RNN", font_size=22, color=WHITE)
    cell = VGroup(box, lab)
    xt = MathTex(r"x_t", font_size=28).next_to(cell, LEFT)
    ht = MathTex(r"h_t", font_size=28).next_to(cell, RIGHT)
    htm = MathTex(r"h_{t-1}", font_size=24).next_to(cell, DOWN)
    title = Text("Recurrent cell", font_size=26, color=WHITE)
    return VGroup(title, VGroup(xt, cell, ht, htm)).arrange(DOWN, buff=0.35)


@register_concept(
    id="lstm_cell",
    domain="recurrent",
    chapter="10.1",
    title="LSTM Cell",
    tags=["lstm"],
)
def build_lstm_cell() -> VGroup:
    title = Text("LSTM gates", font_size=26, color=WHITE)
    eq = MathTex(r"i_t,f_t,o_t,c_t,h_t", font_size=30)
    note = Text("Input / forget / output gates + cell state", font_size=20, color=DEFAULT_THEME.soft)
    return VGroup(title, eq, note).arrange(DOWN, buff=0.35)


@register_concept(
    id="gru_cell",
    domain="recurrent",
    chapter="10.2",
    title="GRU Cell",
    stub=True,
    tags=["gru"],
)
def build_gru_cell() -> VGroup:
    from manim_ai.core.base import stub_concept

    return stub_concept("GRU", r"z_t, r_t, \tilde h_t, h_t")

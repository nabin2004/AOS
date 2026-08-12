"""CNN architecture diagrams (d2l Ch 7.6, 8.6)."""

from __future__ import annotations

from manim import DOWN, LEFT, RIGHT, RoundedRectangle, MathTex, Text, VGroup, WHITE

from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


def _block(label: str, color=None) -> VGroup:
    color = color or DEFAULT_THEME.primary
    box = RoundedRectangle(width=1.6, height=0.7, corner_radius=0.1, color=color, fill_opacity=0.25)
    txt = Text(label, font_size=18, color=WHITE)
    return VGroup(box, txt)


@register_concept(
    id="lenet",
    domain="convolutional",
    chapter="7.6",
    title="LeNet",
    tags=["cnn", "architecture"],
    stub=True,
)
def build_lenet() -> VGroup:
    parts = [
        _block("Conv"),
        _block("Pool"),
        _block("Conv"),
        _block("Pool"),
        _block("FC"),
        _block("Out"),
    ]
    row = VGroup(*parts).arrange(RIGHT, buff=0.2)
    title = Text("LeNet", font_size=28, color=WHITE)
    return VGroup(title, row).arrange(DOWN, buff=0.35)


@register_concept(
    id="resnet_block",
    domain="convolutional",
    chapter="8.6",
    title="Residual Block",
    tags=["cnn", "resnet"],
)
def build_resnet_block() -> VGroup:
    main = VGroup(_block("Conv"), _block("Conv")).arrange(DOWN, buff=0.25)
    skip = Text("identity / skip", font_size=18, color=DEFAULT_THEME.residual)
    plus = MathTex(r"+", font_size=36)
    out = _block("Out", color=DEFAULT_THEME.residual)
    body = VGroup(main, plus, out).arrange(RIGHT, buff=0.35)
    skip.next_to(body, UP, buff=0.2)
    title = Text("ResNet residual block", font_size=26, color=WHITE)
    return VGroup(title, body, skip).arrange(DOWN, buff=0.3)

"""Training loop pipeline (d2l experiments)."""

from __future__ import annotations

from manim import DOWN, RIGHT, RoundedRectangle, Text, VGroup, WHITE

from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


def _step(label: str) -> VGroup:
    box = RoundedRectangle(width=1.8, height=0.7, corner_radius=0.1, color=DEFAULT_THEME.secondary, fill_opacity=0.25)
    return VGroup(box, Text(label, font_size=16, color=WHITE))


@register_concept(
    id="training_loop",
    domain="experiments",
    chapter="12",
    title="Training Loop",
    tags=["training"],
)
def build_training_loop() -> VGroup:
    steps = VGroup(
        _step("Batch"),
        _step("Forward"),
        _step("Loss"),
        _step("Backward"),
        _step("Optim step"),
    ).arrange(RIGHT, buff=0.15)
    title = Text("Training step", font_size=26, color=WHITE)
    return VGroup(title, steps).arrange(DOWN, buff=0.35)

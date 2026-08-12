"""Loss surface placeholder (d2l Ch 12.1)."""

from __future__ import annotations

from manim import DOWN, MathTex, Text, VGroup, WHITE

from manim_ai.core.registry import register_concept
from manim_ai.fundamentals.calculus import build_gradient_descent_path


@register_concept(
    id="loss_surface",
    domain="optimization",
    chapter="12.1",
    title="Loss Landscape (1D)",
    tags=["optimization"],
)
def build_loss_surface() -> VGroup:
    return build_gradient_descent_path()

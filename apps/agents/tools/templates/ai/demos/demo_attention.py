"""Demo: self-attention weights."""

from manim import *

from manim_ai import get_concept


class DemoAttention(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"
        viz = get_concept("self_attention").build(tokens=["I", "love", "AI"])
        viz.scale(0.9).move_to(ORIGIN)
        self.play(FadeIn(viz), run_time=1.0)
        self.wait(1.5)

"""Demo: MLP forward / backward diagram."""

from manim import *

from manim_ai import get_concept


class DemoMLPForwardBack(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"
        viz = get_concept("forward_backward").build()
        viz.move_to(ORIGIN)
        self.play(FadeIn(viz), run_time=1.0)
        self.wait(1.5)

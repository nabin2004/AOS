"""Demo: tensor broadcasting."""

from manim import *

from manim_ai import get_concept


class DemoTensorBroadcast(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a2e"
        viz = get_concept("broadcasting").build()
        viz.move_to(ORIGIN)
        self.play(FadeIn(viz), run_time=1.0)
        self.wait(1.5)

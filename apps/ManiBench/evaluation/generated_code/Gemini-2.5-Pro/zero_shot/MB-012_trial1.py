from manim import *
import numpy as np

class WindmillProblem(Scene):
    """
    An animation of the Windmill Problem.
    A line continuously sweeps through a set of n points,
    always passing through at least two of them.
    """
    def construct(self):
        # --- CONFIGURATION ---
        N_POINTS = 7
        POINT_COORDS = self._generate_points(N_POINTS, x_range=(-6, 6), y_range=(-3.5, 3.5))
        
        # 1. --- INTRODUCTION AND SETUP ---
        title = Text("The Windmill Problem", font_size=48).to_edge(UP)
        subtitle = Text(
            "A line sweeps continuously, always pivoting on a point to maintain contact with at least two points.",
            font_size=24, t2w={'pivoting': BOLD}
        ).next_to(title, DOWN, buff=0.2)

        self.play(Write(title), FadeIn(subtitle, shift=DOWN))
        self.wait(1.5)
        self.play(FadeOut(subtitle))

        # 2. --- CREATE THE POINTS ---
        dots = VGroup(*[Dot(p, radius=0.1, color=WHITE) for p in POINT_COORDS])
        self.play(LaggedStart(*[Create(dot) for dot in dots],
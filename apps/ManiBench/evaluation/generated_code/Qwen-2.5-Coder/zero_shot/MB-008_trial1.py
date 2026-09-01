from manim import *

class ChainRuleAnimation(Scene):
    def construct(self):
        # Define the functions
        g = lambda x: x**
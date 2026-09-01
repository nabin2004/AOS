from manim import *

class TaylorSeriesExample(Scene):
    def construct(self):
        # Define the function and its Taylor series
        x = Symbol('x')
        func = sin(x)
        taylor_series = [func.series(x, , n).removeO() for n in range(
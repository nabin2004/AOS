from manim import *

class TaylorSeriesSin(Scene):
    """
    An animation showing the Taylor series expansion of sin(x) around x=0.
    """
    def construct(self):
        # 1. Setup Axes and Title
        axes = Axes(
            x_range=[-10, 10, 1],
            y_range=[-2.5, 2.5, 1],
            x_length=12,
            y_length=5,
            axis_config={"color": BLUE},
        ).to_edge(DOWN)
        x_axis_label = axes.get_x_axis_label("x")
        y_axis_label = axes.get_y_axis_label("f(x)")

        title = Title("Taylor Series Expansion of sin(x)")
        self.play(Write(title))
        self.play(Create(axes), Write(x_axis_label), Write(y_axis_label))

        # 2. Plot original function sin(x)
        func_graph = axes.plot(
            lambda x: np.sin(x),
            color=BLACK,
            x_range=[-10, 10]
        )
        func_label = axes.get_graph_label(func_graph, "\\sin(x)", x_val=PI, direction=UP)
        self.play
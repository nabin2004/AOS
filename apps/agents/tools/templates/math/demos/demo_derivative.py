"""Demo: derivative tangent with animated reveal (Manim default colors)."""

from manim import *

from manim_math.compute import derivative_at, sample_function


class DemoDerivative(Scene):
    def construct(self):
        title = Text("Derivative as slope of the tangent", font_size=36)
        title.to_edge(UP)
        self.play(Write(title), run_time=0.8)

        f = lambda x: x**2
        x0 = 1.0
        y0, slope = derivative_at(f, x0)
        xs, ys = sample_function(f, -1.5, 2.5, n=120)

        axes = Axes(
            x_range=[-2, 3, 1],
            y_range=[-0.5, 6, 1],
            x_length=7,
            y_length=4.2,
            tips=False,
            axis_config={"include_numbers": True, "font_size": 20},
        ).shift(DOWN * 0.3)

        self.play(Create(axes), run_time=0.8)

        curve = axes.plot_line_graph(
            x_values=[float(x) for x in xs],
            y_values=[float(y) for y in ys],
            add_vertex_dots=False,
            line_color=BLUE,
        )["line_graph"]
        curve_label = MathTex(r"f(x)=x^2", font_size=32, color=BLUE).next_to(axes, UR, buff=0.1)
        self.play(Create(curve), FadeIn(curve_label), run_time=1.2)

        point = Dot(axes.c2p(x0, y0), color=YELLOW, radius=0.1)
        point_lab = MathTex(rf"({x0:g},{y0:g})", font_size=28, color=YELLOW).next_to(point, UR, buff=0.1)
        self.play(GrowFromCenter(point), FadeIn(point_lab), run_time=0.6)

        x1, x2 = x0 - 0.9, x0 + 0.9
        tangent = DashedLine(
            axes.c2p(x1, y0 + slope * (x1 - x0)),
            axes.c2p(x2, y0 + slope * (x2 - x0)),
            color=RED,
            stroke_width=4,
        )
        slope_lab = MathTex(rf"f'({x0:g})={slope:g}", font_size=34, color=RED).to_edge(DOWN)
        self.play(Create(tangent), run_time=0.9)
        self.play(Write(slope_lab), run_time=0.7)
        self.play(Indicate(tangent, color=RED), Indicate(point, color=YELLOW), run_time=0.8)
        self.wait(1.2)

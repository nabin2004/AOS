from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define functions
        f = lambda x: 0.5 * x**2
        f_prime = lambda x: x

        # Axes
        axes_f = Axes(x_range=[-3, 3], y_range=[-1, 5], axis_config={"include_numbers": True})
        axes_f_prime = Axes(x_range=[-3, 3], y_range=[-1, 3], axis_config={"include_numbers": True}, x_length=axes_f.x_length)
        axes_area = Axes(x_range=[-3, 3], y_range=[-1, 5], axis_config={"include_numbers": True})

        # Plots
        graph_f = axes_f.plot(f, color=BLUE)
        graph_f_prime = axes_f_prime.plot(f_prime, color=GREEN)

        # Labels
        f_label = MathTex("f(x) = 0.5x^2").to_corner(UR)
        f_prime_label = MathTex("f'(x) = x").to_corner(UR)

        # Initial x value
        x_val = 1.5

        # Vertical line
        vertical_line = VerticalLine(axes_f_prime.c2p(0, 0), axes_f_prime.c2p(0, 0), color=RED)

        # Area under f'(x)
        area = axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)

        # Accumulated area graph
        graph_accumulated_area = axes_area.plot(lambda x: 0.5 * x**2, color=ORANGE)

        # f(0)
        f_0 = f(0)
        dot_f_0 = Dot(axes_area.c2p(0, f_0), color=PURPLE)
        f_0_label = MathTex(f"f(0) = {f_0}").next_to(dot_f_0, DOWN)

        # Equation
        equation = MathTex(r"\int_{0}^{x} f'(t) \, dt = f(x) - f(0)").to_corner(DL)

        # Initial scene
        self.play(Create(axes_f), Create(axes_f_prime), Create(axes_area), Write(f_label), Write(f_prime_label))
        self.play(Create(graph_f), Create(graph_f_prime), Create(graph_accumulated_area))
        self.play(Create(vertical_line), Create(area))
        self.play(Create(dot_f_0), Write(f_0_label), Write(equation))
        self.wait(1)

        # Animation loop
        for x in [0.5, 1.5, 2.5]:
            x_val = x
            new_area = axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)
            new_vertical_line = VerticalLine(axes_f_prime.c2p(x_val, 0), axes_f_prime.c2p(x_val, f_prime(x_val)), color=RED)
            
            self.play(
                Transform(vertical_line, new_vertical_line),
                Transform(area, new_area),
                RunTime(0.5)
            )
            self.wait(0.5)
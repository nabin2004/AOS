from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define functions
        f = lambda x: 0.5 * x**2
        f_prime = lambda x: x

        # Axes
        axes_f = Axes(x_range=[-3, 3], y_range=[-1, 5], axis_config={"include_numbers": True})
        axes_f_prime = Axes(x_range=[-3, 3], y_range=[-1, 3], axis_config={"include_numbers": True})
        axes_area = Axes(x_range=[-3, 3], y_range=[-1, 5], axis_config={"include_numbers": True})

        # Plots
        graph_f = axes_f.plot(f, color=BLUE)
        graph_f_prime = axes_f_prime.plot(f_prime, color=GREEN)

        # Labels
        f_label = MathTex("f(x) = 0.5x^2").to_corner(UR)
        f_prime_label = MathTex("f'(x) = x").to_corner(UR)
        area_label = MathTex("A(x) = \\int_0^x f'(t) dt").to_corner(UR)

        # Initial x value
        x_val = 1.5

        # Vertical line
        vertical_line = VerticalLine(axes_f_prime.c2p(x_val, 0), axes_f_prime.c2p(x_val, f_prime(x_val)), color=RED)

        # Area under f'(x)
        area = axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)

        # Accumulated area graph
        graph_area = axes_area.plot(lambda x: 0.5 * x**2, color=ORANGE)

        # f(0)
        f_0 = axes_area.c2p(0, f(0))
        dot_f_0 = Dot(f_0, color=PURPLE)
        f_0_label = MathTex("f(0) = 0").next_to(dot_f_0, DOWN)

        # f(x)
        f_x = axes_area.c2p(x_val, f(x_val))
        dot_f_x = Dot(f_x, color=PURPLE)
        f_x_label = MathTex("f(x)").next_to(dot_f_x, DOWN)

        # Equation
        equation = MathTex("\\int_0^x f'(t) dt = f(x) - f(0)").to_corner(DL)

        # Initial scene
        self.play(Create(axes_f), Write(f_label), Create(graph_f))
        self.play(Create(axes_f_prime), Write(f_prime_label), Create(graph_f_prime))
        self.wait(1)

        # Animate area accumulation
        self.play(Create(vertical_line))
        self.play(Create(area))
        self.wait(0.5)

        # Show accumulated area graph
        self.play(Create(axes_area), Create(graph_area), Write(area_label))
        self.play(Create(dot_f_0), Write(f_0_label), Create(dot_f_x), Write(f_x_label))
        self.play(Write(equation))
        self.wait(2)

        # Animate several x values
        for x in [0.5, 1.0, 2.0, 2.5]:
            self.play(
                vertical_line.animate.move_to(axes_f_prime.c2p(x, 0)),
                area.animate.generate_target(axes_f_prime.get_area(f_prime, x_range=[0, x], color=YELLOW, opacity=0.5)),
                dot_f_x.animate.move_to(axes_area.c2p(x, f(x))),
                f_x_label.animate.move_to(axes_area.c2p(x, f(x)) + DOWN * 0.5)
            )
            self.play(area.animate.become(axes_f_prime.get_area(f_prime, x_range=[0, x], color=YELLOW, opacity=0.5)))
            self.wait(0.5)

        self.wait(1)
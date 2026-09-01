from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define the function f(x) = x^2
        f = lambda x: x**2
        f_prime = lambda x: 2*x

        # Create axes for f(x)
        axes_f = Axes(
            x_range=[-3, 3, 1],
            y_range=[0, 9, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True}
        )
        axes_f.add_coordinate_labels()
        graph_f = axes_f.plot(f, x_range=[-3, 3], color=BLUE)
        axes_f.y_axis.label = "f(x)"
        axes_f.x_axis.label = "x"

        # Create axes for f'(x)
        axes_f_prime = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 6, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True}
        )
        axes_f_prime.add_coordinate_labels()
        graph_f_prime = axes_f_prime.plot(f_prime, x_range=[-3, 3], color=GREEN)
        axes_f_prime.y_axis.label = "f'(x)"
        axes_f_prime.x_axis.label = "x"

        # Create axes for the integral (accumulated area)
        axes_integral = Axes(
            x_range=[-3, 3, 1],
            y_range=[0, 9, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True}
        )
        axes_integral.add_coordinate_labels()
        axes_integral.y_axis.label = "∫₀ˣ f'(t) dt"
        axes_integral.x_axis.label = "x"

        # Initial setup
        self.play(Create(axes_f), Create(graph_f))
        self.play(Create(axes_f_prime), Create(graph_f_prime))

        # Animate the area under f'(x) accumulating
        x_val = 0.5
        area = axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)
        self.play(Create(area))

        # Vertical line sweeping the area
        line = VerticalLine(axes_f_prime.c2p(x_val, 0), axes_f_prime.c2p(x_val, f_prime(x_val)), color=RED)
        self.play(Create(line))

        # Display the accumulated area (f(x))
        integral_graph = axes_integral.plot(f, x_range=[0, x_val], color=PURPLE)
        self.play(Create(axes_integral), Create(integral_graph))

        # Demonstrate the equation ∫₀ˣ f'(t) dt = f(x) - f(0)
        equation = MathTex("∫₀ˣ f'(t) dt = f(x) - f(0)")
        equation.to_edge(UP)
        self.play(Write(equation))

        # Animate several values of x
        for x_val in [1, 1.5, 2, 2.5]:
            area = axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)
            integral_graph = axes_integral.plot(f, x_range=[0, x_val], color=PURPLE)

            self.play(
                Transform(area, axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)),
                Transform(integral_graph, axes_integral.plot(f, x_range=[0, x_val], color=PURPLE)),
                Transform(line, VerticalLine(axes_f_prime.c2p(x_val, 0), axes_f_prime.c2p(x_val, f_prime(x_val)), color=RED))
            )
            self.wait(1)

        self.play(FadeOut(equation, axes_f, graph_f, axes_f_prime, graph_f_prime, axes_integral, integral_graph, area, line))
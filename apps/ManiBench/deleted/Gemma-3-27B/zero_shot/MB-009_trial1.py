from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define the function and its derivative
        f = lambda x: 0.5 * x**2 + x
        f_prime = lambda x: x + 1

        # Create axes
        ax_f = Axes(
            x_range=[-3, 5, 1],
            y_range=[-2, 10, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        ax_f.add_coordinate_labels()
        ax_f_prime = Axes(
            x_range=[-3, 5, 1],
            y_range=[-1, 5, 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True},
        )
        ax_f_prime.add_coordinate_labels()
        ax_area = Axes(
            x_range=[-3, 5, 1],
            y_range=[-2, 10, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        ax_area.add_coordinate_labels()

        # Plot the function and its derivative
        graph_f = ax_f.plot(f, x_range=[-3, 5], color=BLUE)
        graph_f_prime = ax_f_prime.plot(f_prime, x_range=[-3, 5], color=RED)

        # Label the graphs
        ax_f.add_label("f(x) = 0.5x² + x", graph_f)
        ax_f_prime.add_label("f'(x) = x + 1", graph_f_prime)

        # Initial x value
        x_val = 2

        # Vertical line for area accumulation
        vertical_line = VGroup()
        vertical_line.add(ax_f_prime.get_vertical_line(x_val, color=GREEN))
        vertical_line.add(ax_f_prime.get_area(f_prime, x_range=[0, x_val], color=GREEN, opacity=0.5))

        # Accumulated area graph
        graph_area = ax_area.plot(f, x_range=[0, x_val], color=YELLOW)
        area_point = Dot(ax_area.c2p(x_val, f(x_val)), color=YELLOW)

        # Equation display
        equation = MathTex(r"\int_{0}^{x} f'(t) \, dt = f(x) - f(0)")
        equation.next_to(ax_f, UP)

        # Initial setup
        self.play(Create(ax_f), Create(ax_f_prime), Create(ax_area))
        self.play(Create(graph_f), Create(graph_f_prime))
        self.play(Create(vertical_line))
        self.play(Create(graph_area), Create(area_point))
        self.play(Write(equation))

        # Animate x value
        for x in [2, 3, 4]:
            self.play(
                vertical_line.animate.set(ax_f_prime.get_vertical_line(x)),
                graph_area.animate.set(ax_area.plot(f, x_range=[0, x])),
                area_point.animate.move_to(ax_area.c2p(x, f(x))),
            )
            self.wait(1)

        # Clean up
        self.play(FadeOut(ax_f, ax_f_prime, ax_area, graph_f, graph_f_prime, vertical_line, graph_area, area_point, equation))
        self.wait(1)
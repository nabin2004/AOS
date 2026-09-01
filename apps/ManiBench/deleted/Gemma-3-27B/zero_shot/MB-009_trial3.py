from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define the function and its derivative
        f = lambda x: 0.5 * x**2 + x
        f_prime = lambda x: x + 1

        # Create axes
        ax_f = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 15, 2],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        ax_f.add_coordinate_labels()
        ax_f_prime = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True},
        )
        ax_f_prime.add_coordinate_labels()
        ax_area = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 15, 2],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        ax_area.add_coordinate_labels()

        # Plot the function and its derivative
        graph_f = ax_f.plot(f, x_range=[0, 5], color=BLUE)
        graph_f_prime = ax_f_prime.plot(f_prime, x_range=[0, 5], color=RED)

        # Label the graphs
        ax_f.add_label("f(x) = 0.5x² + x", graph_f)
        ax_f_prime.add_label("f'(x) = x + 1", graph_f_prime)

        # Initial x value
        x_val = 2

        # Vertical line for area accumulation
        vertical_line = VGroup()
        vertical_line.add(ax_f_prime.get_vertical_line(x_val, color=GREEN))
        vertical_line.add(ax_f_prime.get_area(f_prime, 0, x_val, color=GREEN, opacity=0.5))

        # Accumulated area graph
        graph_area = ax_area.plot(f, x_range=[0, x_val], color=YELLOW)
        area_label = ax_area.get_value_mark(x_val, f(x_val), color=YELLOW)
        area_label.add_text("f(x)", color=YELLOW)

        # Equation display
        equation = MathTex(
            "\\int_{0}^{x} f'(t) \, dt = f(x) - f(0)"
        ).next_to(ax_f, DOWN, buff=0.5)

        # Initial display
        self.play(Create(ax_f), Create(graph_f))
        self.play(Create(ax_f_prime), Create(graph_f_prime))
        self.play(Create(ax_area), Create(graph_area), Create(area_label))
        self.play(Create(vertical_line))
        self.play(Write(equation))

        # Animate x value
        for x in [2, 3, 4]:
            self.play(
                vertical_line.animate.set(ax_f_prime.get_vertical_line(x)),
                ax_f_prime.get_area(f_prime, 0, x).animate.become(ax_f_prime.get_area(f_prime, 0, x, color=GREEN, opacity=0.5)),
                graph_area.animate.set(ax_area.plot(f, x_range=[0, x], color=YELLOW)),
                area_label.animate.move_to(ax_area.get_value_mark(x, f(x), color=YELLOW)),
            )
            self.wait(1)

        self.play(FadeOut(ax_f, ax_f_prime, ax_area, graph_f, graph_f_prime, graph_area, vertical_line, equation, area_label))
        self.wait(1)
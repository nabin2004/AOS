from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define the function and its derivative
        f = lambda x: 0.5 * x**2
        f_prime = lambda x: x

        # Create axes
        axes_f = Axes(
            x_range=[-3, 3, 1],
            y_range=[0, 5, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        axes_f_prime = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 4, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        axes_f.add_coordinate_labels()
        axes_f_prime.add_coordinate_labels()

        # Plot the function and its derivative
        graph_f = axes_f.plot(f, x_range=[-3, 3], color=BLUE)
        graph_f_prime = axes_f_prime.plot(f_prime, x_range=[-3, 3], color=RED)

        # Label the functions
        f_label = Tex("f(x) = 0.5x^2", weight=0.8, critical=True).next_to(axes_f, UP)
        f_prime_label = Tex("f'(x) = x", weight=0.8, critical=True).next_to(axes_f_prime, UP)

        # Show the function and derivative
        self.play(Create(axes_f), Create(axes_f_prime))
        self.play(Create(graph_f), Create(graph_f_prime))
        self.play(Write(f_label), Write(f_prime_label))
        self.wait(2)

        # Animate the area under f'(x)
        x_val = ValueTracker(0)
        area = always_redraw(lambda: axes_f_prime.get_area(f_prime, x_min=0, x_max=x_val.get_value(), color=GREEN, opacity=0.5))
        sweep_line = always_redraw(lambda: VerticalLine(axes_f_prime.c2p(x_val.get_value(), 0), axes_f_prime.c2p(x_val.get_value(), f_prime(x_val.get_value())), color=YELLOW, stroke_width=2, dash_pattern=[6, 6]))

        # Display the accumulated area
        accumulated_area_text = Tex("Accumulated Area", weight=0.8, critical=True).to_edge(UR)
        area_value_text = always_redraw(lambda: Tex(f"${f(x_val.get_value()):.2f}$", weight=0.8, critical=True).next_to(accumulated_area_text, DOWN))

        self.play(Create(area), Create(sweep_line))
        self.play(Write(accumulated_area_text), Write(area_value_text))

        self.play(x_val.animate.set_value(2), run_time=3)
        self.wait(2)

        # Demonstrate the FTC formula
        ftc_formula = Tex("∫₀ˣ f'(t) dt = f(x) − f(0)", weight=0.7, critical=True).to_edge(DL)
        self.play(Write(ftc_formula))
        self.wait(2)

        # Animate several values of x
        for x in [1, 2.5, -1]:
            self.play(x_val.animate.set_value(x), run_time=2)
            self.wait(1)
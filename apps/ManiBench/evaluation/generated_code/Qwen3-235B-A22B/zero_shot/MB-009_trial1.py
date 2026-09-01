from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define the function f(x) and its derivative f'(x)
        def f(x):
            return 0.5 * x**2 + x + 1

        def f_prime(x):
            return x + 1

        # Axes for f(x)
        ax1 = Axes(
            x_range=[-1, 4, 1],
            y_range=[0, 10, 2],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True}
        ).shift(UP * 2)
        ax1_labels = ax1.get_axis_labels(x_label="x", y_label="f(x)")

        # Plot f(x)
        graph_f = ax1.plot(f, x_range=[-1, 4], color=BLUE, stroke_width=4)
        graph_f_label = MathTex("f(x) = \\frac{1}{2}x^2 + x + 1", color=BLUE).scale(0.6).next_to(ax1, UP, buff=0.2)

        # Axes for f'(x)
        ax2 = Axes(
            x_range=[-1, 4, 1],
            y_range=[0, 5, 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True}
        ).shift(DOWN * 2)
        ax2_labels = ax2.get_axis_labels(x_label="x", y_label="f'(x)")

        # Plot f'(x)
        graph_f_prime = ax2.plot(f_prime, x_range=[-1, 4], color=RED, stroke_width=4)
        graph_f_prime_label = MathTex("f'(x) = x + 1", color=RED).scale(0.6).next_to(ax2, UP, buff=0.2)

        # Accumulated area graph (should match f(x) - f(0))
        def accumulated_area(x):
            return f(x) - f(0)

        ax3 = Axes(
            x_range=[-1, 4, 1],
            y_range=[0, 10, 2],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True}
        ).shift(UP * 2)
        ax3_labels = ax3.get_axis_labels(x_label="x", y_label="\\int_0^x f'(t) dt")

        # Plot of accumulated area
        graph_area = ax3.plot(accumulated_area, x_range=[0, 4], color=GREEN, stroke_width=4)
        graph_area_label = MathTex("\\int_0^x f'(t) dt", color=GREEN).scale(0.6).next_to(ax3, UP, buff=0.2)

        # Show f(x) plot
        self.play(Create(ax1), Write(ax1_labels))
        self.play(Create(graph_f), Write(graph_f_label))
        self.wait(0.5)

        # Show f'(x) plot below
        self.play(Create(ax2), Write(ax2_labels))
        self.play(Create(graph_f_prime), Write(graph_f_prime_label))
        self.wait(0.5)

        # Show the area accumulation axes and label
        self.play(
            ReplacementTransform(ax1.copy(), ax3),
            ReplacementTransform(ax1_labels.copy(), ax3_labels),
            ReplacementTransform(graph_f_label.copy(), graph_area_label)
        )
        self.wait(0.5)

        # Create moving vertical line and area
        moving_x = ValueTracker(0.5)
        x_max = 4

        # Area under f'(x)
        area = always_redraw(
            lambda: ax2.get_area(
                graph_f_prime,
                x_range=[0, moving_x.get_value()],
                color=RED_E,
                opacity=0.5
            )
        )

        # Dot on f'(x) graph
        dot_f_prime = always_redraw(
            lambda: Dot(
                ax2.c2p(moving_x.get_value(), f_prime(moving_x.get_value())),
                color=YELLOW
            )
        )

        # Vertical line from f'(x) to area graph
        vertical_line = always_redraw(
            lambda: DashedLine(
                ax2.c2p(moving_x.get_value(), 0),
                ax3.c2p(moving_x.get_value(), 0),
                color=GRAY
            )
        )

        # Dot on accumulated area graph
        dot_area = always_redraw(
            lambda: Dot(
                ax3.c2p(moving_x.get_value(), accumulated_area(moving_x.get_value())),
                color=YELLOW
            )
        )

        # Dot on original f(x) graph
        dot_f = always_redraw(
            lambda: Dot(
                ax1.c2p(moving_x.get_value(), f(moving_x.get_value())),
                color=YELLOW
            )
        )

        # Moving vertical line on all graphs
        vertical_line_f = always_redraw(
            lambda: Line(
                ax1.c2p(moving_x.get_value(), 0),
                ax1.c2p(moving_x.get_value(), f(moving_x.get_value())),
                color=BLUE_E
            )
        )

        vertical_line_f_prime = always_redraw(
            lambda: Line(
                ax2.c2p(moving_x.get_value(), 0),
                ax2.c2p(moving_x.get_value(), f_prime(moving_x.get_value())),
                color=RED_E
            )
        )

        # Show area under f'(x)
        self.play(FadeIn(area), Create(vertical_line_f_prime), Create(dot_f_prime))
        self.play(Create(vertical_line), Create(dot_area), Create(dot_f), Create(vertical_line_f))
        self.add(graph_area)  # Show accumulated area graph (was hidden until now)

        # Animate the sweep from left to right
        self.play(
            moving_x.animate.set_value(x_max),
            rate_func=linear,
            run_time=8
        )

        # Show the equation
        equation = MathTex(
            "\\int_0^x f'(t) \\, dt = f(x) - f(0)",
            color=WHITE
        ).scale(0.8).to_edge(UP)

        # Highlight that the graphs are equal
        self.play(Write(equation))
        self.wait(1)

        # Test a few specific values
        test_values = [1, 2, 3]
        for x_val in test_values:
            self.play(moving_x.animate.set_value(x_val), run_time=1.5)
            # Show calculation
            calc = MathTex(
                f"\\int_0^{{{x_val}}} f'(t) dt = {accumulated_area(x_val):.1f},\\quad",
                f"f({x_val}) - f(0) = {f(x_val) - f(0):.1f}"
            ).scale(0.6).next_to(equation, DOWN)
            self.play(Write(calc), run_time=1)
            self.wait(1)
            self.play(FadeOut(calc), run_time=0.5)

        self.wait(2)
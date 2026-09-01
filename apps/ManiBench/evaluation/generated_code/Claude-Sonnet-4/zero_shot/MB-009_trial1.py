from manim import *
import numpy as np

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Set up axes
        axes_f = Axes(
            x_range=[-1, 4, 1],
            y_range=[-1, 5, 1],
            x_length=6,
            y_length=3,
            axis_config={"color": BLUE},
        ).shift(UP * 2)
        
        axes_fprime = Axes(
            x_range=[-1, 4, 1],
            y_range=[-1, 3, 1],
            x_length=6,
            y_length=2.5,
            axis_config={"color": BLUE},
        ).shift(DOWN * 1.5)
        
        # Define functions
        def f(x):
            return 0.3 * x**2 + 0.5 * x + 1
        
        def f_prime(x):
            return 0.6 * x + 0.5
        
        # Create function graphs
        f_graph = axes_f.plot(f, color=RED, x_range=[-0.5, 3.5])
        f_prime_graph = axes_fprime.plot(f_prime, color=GREEN, x_range=[-0.5, 3.5])
        
        # Labels
        f_label = MathTex("f(x) = 0.3x^2 + 0.5x + 1", color=RED).scale(0.7).next_to(axes_f, UP)
        f_prime_label = MathTex("f'(x) = 0.6x + 0.5", color=GREEN).scale(0.7).next_to(axes_fprime, UP)
        
        # Show initial setup
        self.play(
            Create(axes_f),
            Create(axes_fprime),
            Write(f_label),
            Write(f_prime_label)
        )
        self.play(
            Create(f_graph),
            Create(f_prime_graph)
        )
        
        # Create vertical line tracker
        x_tracker = ValueTracker(0)
        
        # Vertical line on both graphs
        v_line_f = always_redraw(
            lambda: axes_f.get_vertical_line(
                axes_f.i2gp(x_tracker.get_value(), f_graph),
                color=YELLOW,
                line_config={"stroke_width": 3}
            )
        )
        
        v_line_fprime = always_redraw(
            lambda: axes_fprime.get_vertical_line(
                axes_fprime.i2gp(x_tracker.get_value(), f_prime_graph),
                color=YELLOW,
                line_config={"stroke_width": 3}
            )
        )
        
        # Area under f'(x) from 0 to x
        area = always_redraw(
            lambda: axes_fprime.get_area(
                f_prime_graph,
                x_range=[0, x_tracker.get_value()],
                color=BLUE,
                opacity=0.5
            )
        )
        
        # Point on f(x) corresponding to current x
        point_f = always_redraw(
            lambda: Dot(
                axes_f.i2gp(x_tracker.get_value(), f_graph),
                color=YELLOW,
                radius=0.08
            )
        )
        
        # Display current x value
        x_value_text = always_redraw(
            lambda: MathTex(f"x = {x_tracker.get_value():.1f}")
            .scale(0.8)
            .next_to(axes_f, RIGHT)
            .shift(UP)
        )
        
        # Display integral value
        integral_text = always_redraw(
            lambda: MathTex(
                f"\\int_0^{{{x_tracker.get_value():.1f}}} f'(t) dt = {f(x_tracker.get_value()) - f(0):.2f}"
            )
            .scale(0.7)
            .next_to(axes_fprime, RIGHT)
        )
        
        # Display f(x) - f(0) value
        function_diff_text = always_redraw(
            lambda: MathTex(
                f"f({x_tracker.get_value():.1f}) - f(0) = {f(x_tracker.get_value()) - f(0):.2f}"
            )
            .scale(0.7)
            .next_to(integral_text, DOWN)
        )
        
        # Add elements
        self.play(
            Create(v_line_f),
            Create(v_line_fprime),
            Create(point_f),
            Write(x_value_text)
        )
        
        # Show the theorem statement
        theorem_text = MathTex(
            "\\text{Fundamental Theorem of Calculus:}",
            "\\int_0^x f'(t) dt = f(x) - f(0)"
        ).scale(0.8).to_edge(UP)
        
        self.play(Write(theorem_text))
        
        # Animate the sweeping
        self.play(Create(area))
        self.play(
            Write(integral_text),
            Write(function_diff_text)
        )
        
        # Animate x from 0 to 3
        self.play(
            x_tracker.animate.set_value(3),
            run_time=4,
            rate_func=linear
        )
        
        self.wait(1)
        
        # Show specific values
        specific_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        
        for val in specific_values:
            self.play(
                x_tracker.animate.set_value(val),
                run_time=0.8
            )
            self.wait(0.5)
        
        # Create accumulated area graph (which should match f(x) - f(0))
        accumulated_points = []
        x_vals = np.linspace(0, 3, 50)
        
        for x_val in x_vals:
            y_val = f(x_val) - f(0)
            accumulated_points.append(axes_f.c2p(x_val, y_val))
        
        accumulated_curve = VMobject()
        accumulated_curve.set_points_smoothly(accumulated_points)
        accumulated_curve.set_color(PURPLE)
        accumulated_curve.set_stroke(width=4)
        
        # Label for accumulated area curve
        accumulated_label = MathTex(
            "\\int_0^x f'(t) dt", color=PURPLE
        ).scale(0.7).next_to(axes_f, LEFT)
        
        self.play(
            Create(accumulated_curve),
            Write(accumulated_label)
        )
        
        # Highlight that they're the same (up to a constant)
        highlight_text = MathTex(
            "\\text{The curves differ by a constant } f(0)"
        ).scale(0.7).to_edge(DOWN)
        
        self.play(Write(highlight_text))
        
        # Final sweep to emphasize
        self.play(
            x_tracker.animate.set_value(0),
            run_time=1
        )
        self.play(
            x_tracker.animate.set_value(3),
            run_time=3,
            rate_func=smooth
        )
        
        self.wait(2)
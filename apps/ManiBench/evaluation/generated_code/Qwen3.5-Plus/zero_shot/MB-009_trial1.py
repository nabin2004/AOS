from manim import *
import numpy as np

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Configuration
        x_min = -1
        x_max = 5
        y_min = -1
        y_max = 6
        
        # Define the function f(x) = 0.5 * x^2 + 1
        # Its derivative f'(x) = x
        func = lambda x: 0.5 * x**2 + 1
        deriv_func = lambda x: x
        
        # Create Axes
        # Top graph: f(x)
        axes_top = Axes(
            x_range=[x_min, x_max, 1],
            y_range=[y_min, y_max, 1],
            x_length=10,
            y_length=4,
            axis_config={"include_tip": True, "include_numbers": False},
        ).shift(UP * 2.5)
        
        labels_top = VGroup(
            axes_top.get_x_axis_label("x"),
            axes_top.get_y_axis_label("f(x)")
        )
        
        # Bottom graph: f'(x)
        axes_bottom = Axes(
            x_range=[x_min, x_max, 1],
            y_range=[-2, 5, 1],
            x_length=10,
            y_length=4,
            axis_config={"include_tip": True, "include_numbers": False},
        ).shift(DOWN * 2.5)
        
        labels_bottom = VGroup(
            axes_bottom.get_x_axis_label("x"),
            axes_bottom.get_y_axis_label("f'(x)")
        )
        
        # Plot curves
        graph_f = axes_top.plot(func, color=BLUE, x_range=[x_min, x_max])
        graph_f_label = MathTex("f(x) = \\frac{1}{2}x^2 + 1", color=BLUE).next_to(axes_top, UR, buff=0.5)
        
        graph_fp = axes_bottom.plot(deriv_func, color=GREEN, x_range=[x_min, x_max])
        graph_fp_label = MathTex("f'(x) = x", color=GREEN).next_to(axes_bottom, DR, buff=0.5)
        
        # Initial Display
        self.play(Create(axes_top), Write(labels_top))
        self.play(Create(graph_f), Write(graph_f_label))
        self.wait(0.5)
        
        self.play(Create(axes_bottom), Write(labels_bottom))
        self.play(Create(graph_fp), Write(graph_fp_label))
        self.wait(1)
        
        # Equation Display
        equation = MathTex(
            "\\int_0^x f'(t) \\, dt = f(x) - f(0)",
            font_size=36
        ).to_edge(UP)
        self.play(Write(equation))
        
        # Animation of Integration
        # We will sweep from x=0 to x=4
        start_x = 0
        end_x = 4
        steps = 40
        
        # Tracker for current x
        x_tracker = ValueTracker(start_x)
        
        # Vertical line on bottom graph (sweeping line)
        vert_line_bottom = always_redraw(lambda: axes_bottom.get_vertical_line(
            axes_bottom.i2gp(x_tracker.get_value(), graph_fp),
            color=WHITE,
            stroke_width=2
        ))
        
        # Area under f'(x) from 0 to x
        area_bottom = always_redraw(lambda: axes_bottom.get_area(
            graph_fp,
            x_range=[0, x_tracker.get_value()],
            color=GREEN,
            opacity=0.3
        ))
        
        # Calculate f(0) for the equation demonstration
        f_0 = func(0)
        
        # Graph of accumulated area (which should match f(x) shifted by f(0))
        # The integral of f'(t) from 0 to x is f(x) - f(0).
        # So we plot g(x) = f(x) - f(0) on the top graph to show correspondence?
        # Actually, the prompt asks to "Display a graph of the accumulated area".
        # Let's plot the integral function I(x) on the top graph dynamically or show it matches the shape.
        # To make it clear, let's plot the theoretical integral curve on the top graph in a different color
        # and show the point moving along it corresponds to the area.
        
        # Integral function I(x) = f(x) - f(0)
        integral_func = lambda x: func(x) - f_0
        graph_integral = axes_top.plot(integral_func, color=YELLOW, x_range=[0, x_max], stroke_width=4)
        graph_integral_label = MathTex("\\int_0^x f'(t)dt", color=YELLOW).next_to(axes_top, UL, buff=0.5)
        
        # Dot on the integral curve
        dot_top = always_redraw(lambda: Dot(
            axes_top.c2p(x_tracker.get_value(), integral_func(x_tracker.get_value())),
            color=YELLOW,
            radius=0.08
        ))
        
        # Dot on the derivative curve (tip of the vertical line)
        dot_bottom = always_redraw(lambda: Dot(
            axes_bottom.c2p(x_tracker.get_value(), deriv_func(x_tracker.get_value())),
            color=WHITE,
            radius=0.08
        ))
        
        # Label for the area value
        area_value_label = always_redraw(lambda: MathTex(
            f"Area = {x_tracker.get_value():.2f}",
            font_size=24
        ).next_to(axes_bottom, RIGHT, buff=0.5))
        
        # Label for the function value
        func_value_label = always_redraw(lambda: MathTex(
            f"f(x)-f(0) = {integral_func(x_tracker.get_value()):.2f}",
            font_size=24,
            color=YELLOW
        ).next_to(axes_top, RIGHT, buff=0.5))

        # Add static elements
        self.play(Create(graph_integral), Write(graph_integral_label))
        
        # Add dynamic elements
        self.add(vert_line_bottom, area_bottom, dot_top, dot_bottom, area_value_label, func_value_label)
        
        # Animate the sweep
        self.play(
            x_tracker.animate.set_value(end_x),
            run_time=4,
            rate_func=linear
        )
        
        self.wait(1)
        
        # Highlight specific points to demonstrate correspondence
        key_values = [1, 2, 3, 4]
        for val in key_values:
            self.play(x_tracker.animate.set_value(val), run_time=0.5)
            self.wait(0.2)
            
        # Final Emphasis
        box = SurroundingRectangle(equation, color=WHITE, buff=0.1)
        self.play(Create(box))
        
        self.wait(2)
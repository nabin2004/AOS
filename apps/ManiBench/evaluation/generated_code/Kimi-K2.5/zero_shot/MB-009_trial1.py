from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Configuration
        x_max = 2.5
        x_step = 0.5
        
        # Create three aligned axes
        axes_top = Axes(
            x_range=[0, x_max, x_step],
            y_range=[0, 5, 1],
            x_length=6,
            y_length=2,
            axis_config={"include_tip": True, "numbers_to_include": [0, 1, 2]},
            tips=False
        )
        
        axes_mid = Axes(
            x_range=[0, x_max, x_step],
            y_range=[0, 3, 0.5],
            x_length=6,
            y_length=2,
            axis_config={"include_tip": True, "numbers_to_include": [0, 1, 2]},
            tips=False
        )
        
        axes_bot = Axes(
            x_range=[0, x_max, x_step],
            y_range=[0, 4, 0.5],
            x_length=6,
            y_length=2,
            axis_config={"include_tip": True, "numbers_to_include": [0, 1, 2]},
            tips=False
        )
        
        # Position axes vertically
        axes_top.to_edge(UP, buff=0.4)
        axes_mid.next_to(axes_top, DOWN, buff=0.9)
        axes_bot.next_to(axes_mid, DOWN, buff=0.9)
        
        # Function definitions
        def f(x):
            return 0.5 * x**2 + 1
            
        def f_prime(x):
            return x
            
        def integral(x):
            return 0.5 * x**2  # f(x) - f(0)
        
        # Create graphs
        graph_f = axes_top.plot(f, color=BLUE, x_range=[0, x_max])
        graph_fprime = axes_mid.plot(f_prime, color=RED, x_range=[0, x_max])
        graph_integral = axes_bot.plot(integral, color=GREEN, x_range=[0, x_max])
        
        # Labels
        label_f = MathTex("f(x) = \\frac{x^2}{2} + 1", color=BLUE).scale(0.7)
        label_f.next_to(axes_top, RIGHT, buff=0.3)
        
        label_fprime = MathTex("f'(x) = x", color=RED).scale(0.7)
        label_fprime.next_to(axes_mid, RIGHT, buff=0.3)
        
        label_integral = MathTex("f(x) - f(0) = \\frac{x^2}{2}", color=GREEN).scale(0.7)
        label_integral.next_to(axes_bot, RIGHT, buff=0.3)
        
        # Initial animation
        self.play(
            Create(axes_top),
            Create(axes_mid),
            Create(axes_bot),
            run_time=2
        )
        self.play(
            Create(graph_f),
            Create(graph_fprime),
            Create(graph_integral),
            Write(label_f),
            Write(label_fprime),
            Write(label_integral),
            run_time=2
        )
        
        # Value tracker for the sweeping animation
        x_tracker = ValueTracker(0.01)
        
        # Dynamic area under f'(x)
        area = always_redraw(lambda: axes_mid.get_area(
            graph_fprime,
            x_range=[0, x_tracker.get_value()],
            color=RED,
            opacity=0.4
        ))
        
        # Vertical line on middle graph (at current x)
        v_line_mid = always_redraw(lambda: Line(
            axes_mid.c2p(x_tracker.get_value(), 0),
            axes_mid.c2p(x_tracker.get_value(), f_prime(x_tracker.get_value())),
            color=YELLOW,
            stroke_width=3
        ))
        
        # Vertical line on bottom graph
        v_line_bot = always_redraw(lambda: Line(
            axes_bot.c2p(x_tracker.get_value(), 0),
            axes_bot.c2p(x_tracker.get_value(), integral(x_tracker.get_value())),
            color=YELLOW,
            stroke_width=3
        ))
        
        # Dot on the integral curve
        dot = always_redraw(lambda: Dot(
            axes_bot.c2p(x_tracker.get_value(), integral(x_tracker.get_value())),
            color=YELLOW,
            radius=0.08
        ))
        
        # Add dynamic elements
        self.add(area, v_line_mid, v_line_bot, dot)
        
        # Equation at bottom
        theorem = MathTex("\\int_0^x f'(t)\\,dt = f(x) - f(0)").scale(0.9)
        theorem.to_edge(DOWN, buff=0.3)
        self.play(Write(theorem))
        
        # Animate the sweeping from x=0 to x=2
        self.play(x_tracker.animate.set_value(2), run_time=6, rate_func=linear)
        self.wait(0.5)
        
        # Demonstrate specific values
        test_values = [0.5, 1.0, 1.5, 2.0]
        
        for x_val in test_values:
            self.play(x_tracker.animate.set_value(x_val), run_time=1.2)
            
            # Calculate values for display
            area_val = 0.5 * x_val**2
            f_at_x = f(x_val)
            f_0 = f(0)
            
            # Create explanatory text
            explanation = MathTex(
                f"\\text{{At }} x = {x_val}: \\quad \\int_0^{{{x_val}}} t\\,dt = {area_val:.2f} = {f_at_x:.2f} - {f_0:.2f}",
                color=YELLOW
            ).scale(0.65)
            explanation.next_to(theorem, UP, buff=0.4)
            
            # Show correspondence with horizontal line on top graph
            h_line_top = Line(
                axes_top.c2p(0, f(x_val)),
                axes_top.c2p(x_val, f(x_val)),
                color=YELLOW,
                stroke_width=2,
                dash_length=0.1
            ).set_dash_ratio(0.5)
            
            self.play(
                Write(explanation),
                Create(h_line_top),
                run_time=0.8
            )
            self.wait(1)
            self.play(
                FadeOut(explanation),
                FadeOut(h_line_top),
                run_time=0.5
            )
        
        # Final sweep to show continuity
        self.play(x_tracker.animate.set_value(2.2), run_time=2)
        self.wait(2)
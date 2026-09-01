from manim import *
import numpy as np
import math

class TaylorSeries(Scene):
    def construct(self):
        # Set background to white and use black for axes/labels
        self.camera.background_color = WHITE
        
        # Create axes
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-2, 2, 1],
            x_length=8,
            y_length=4,
            axis_config={"color": BLACK},
        ).to_edge(LEFT)
        axes_labels = axes.get_axis_labels(x_label="x", y_label="y").set_color(BLACK)
        
        # Original function: sin(x)
        original_func = axes.plot(np.sin, color=BLACK)
        original_label = axes.get_graph_label(original_func, label='\\sin(x)', color=BLACK)
        
        # Precomputed Taylor formulas and colors
        formulas_str = [
            "0",
            "x",
            "x - \\frac{x^3}{3!}",
            "x - \\frac{x^3}{3!} + \\frac{x^5}{5!}",
            "x - \\frac{x^3}{3!} + \\frac{x^5}{5!} - \\frac{x^7}{7!}",
            "x - \\frac{x^3}{3!} + \\frac{x^5}{5!} - \\frac{x^7}{7!} + \\frac{x^9}{9!}",
            "x - \\frac{x^3}{3!} + \\frac{x^5}{5!} - \\frac{x^7}{7!} + \\frac{x^9}{9!} - \\frac{x^{11}}{11!}",
            "x - \\frac{x^3}{3!} + \\frac{x^5}{5!} - \\frac{x^7}{7!} + \\frac{x^9}{9!} - \\frac{x^{11}}{11!} + \\frac{x^{13}}{13!}",
        ]
        colors = [GRAY, RED, BLUE, GREEN, PURPLE, ORANGE, PINK, YELLOW]
        
        # Formula display setup
        formula_title = Text("Taylor Polynomial:", color=BLACK).to_corner(UP+LEFT)
        formula_display = MathTex("", color=BLACK).next_to(formula_title, DOWN, buff=0.2).to_edge(LEFT)
        
        # Convergence text
        convergence_text = Text("Higher-order terms improve approximation", 
                                color=BLACK, font_size=24).to_corner(DOWN)
        
        # Add static elements
        self.add(axes, axes_labels, original_func, original_label, formula_title)
        
        # Animation sequence
        current_graph = None
        for n in range(8):
            # Create Taylor polynomial function
            def taylor_func(x, n_terms=n+1):
                result = 0
                for i in range(n_terms):
                    exponent = 2*i + 1
                    sign = 1 if i % 2 == 0 else -1
                    term = sign * (x**exponent) / math.factorial(exponent)
                    result += term
                return result
            
            # Create graph and formula
            graph = axes.plot(taylor_func, color=colors[n])
            formula = MathTex(formulas_str[n], color=BLACK).move_to(formula_display)
            
            # First frame
            if n == 0:
                current_graph = graph
                self.add(current_graph, formula)
                self.wait(0.5)
                continue
            
            # Subsequent frames
            self.play(
                ReplacementTransform(current_graph, graph),
                ReplacementTransform(formula_display, formula),
                run_time=1.5
            )
            current_graph = graph
            formula_display = formula
            self.wait(0.5)
        
        # Add convergence text at the end
        self.play(Write(convergence_text))
        self.wait(2)
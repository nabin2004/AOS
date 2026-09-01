from manim import *
import numpy as np

class TaylorSeriesExpansion(Scene):
    def construct(self):
        # Configuration
        func = np.sin
        func_name = "sin(x)"
        max_degree = 7
        x_range = [-2 * PI, 2 * PI]
        y_range = [-2, 2]
        
        # Create axes
        axes = Axes(
            x_range=x_range,
            y_range=y_range,
            x_length=10,
            y_length=6,
            axis_config={"include_tip": True, "include_numbers": False},
        ).shift(DOWN * 0.5)
        
        axes_labels = axes.get_axis_labels(x_label="x", y_label="f(x)")
        
        # Plot original function
        original_graph = axes.plot(func, color=BLACK, stroke_width=3)
        original_label = MathTex(r"f(x) = \sin(x)").to_corner(UL).set_color(BLACK)
        
        # Taylor series coefficients for sin(x) at x=0
        # sin(x) = x - x^3/3! + x^5/5! - x^7/7! + ...
        terms = [
            (0, 0),          # 0th degree (constant 0)
            (1, 1),          # 1st degree (x)
            (3, -1/6),       # 3rd degree (-x^3/3!)
            (5, 1/120),      # 5th degree (x^5/5!)
            (7, -1/5040),    # 7th degree (-x^7/7!)
        ]
        
        # Colors for each term
        term_colors = [WHITE, RED, BLUE, GREEN, YELLOW, ORANGE, PINK, PURPLE]
        
        # Function to compute partial sum
        def taylor_partial_sum(x, degree):
            result = 0
            for deg, coeff in terms:
                if deg <= degree:
                    result += coeff * (x ** deg)
            return result
        
        # Create initial partial sum (0th order)
        current_sum_graph = axes.plot(
            lambda x: taylor_partial_sum(x, 0),
            color=term_colors[0],
            stroke_width=3
        )
        
        # Title
        title = Text("Taylor Series Expansion", font_size=36).to_edge(UP)
        subtitle = MathTex(r"P_n(x) = \sum_{k=0}^{n} \frac{f^{(k)}(0)}{k!} x^k", font_size=24).next_to(title, DOWN)
        
        # Convergence explanation
        convergence_text = Text(
            "Higher-order terms improve approximation",
            font_size=20,
            color=BLUE
        ).to_edge(DOWN)
        
        # Coefficients display
        coeff_display = VGroup()
        coeff_lines = []
        for i, (deg, coeff) in enumerate(terms):
            if deg == 0:
                term_tex = f"{coeff:.0f}"
            elif deg == 1:
                term_tex = f"{coeff:+.1f}x"
            else:
                factorial = np.math.factorial(deg)
                sign = "+" if coeff > 0 else "-"
                term_tex = f"{sign} \\frac{{x^{deg}}}{{{factorial}}}"
            
            line = MathTex(term_tex, font_size=28)
            coeff_lines.append(line)
        
        coeff_display = VGroup(*coeff_lines).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        coeff_display.to_corner(UR).shift(DOWN * 0.5)
        
        # Animation sequence
        self.play(Write(title), Write(subtitle))
        self.play(Create(axes), Write(axes_labels))
        self.play(Create(original_graph), Write(original_label))
        self.play(Write(convergence_text))
        self.play(Create(coeff_display))
        
        # Animate partial sums
        current_graph = current_sum_graph
        self.play(Create(current_graph))
        
        # Update graph for each term
        for i in range(1, len(terms)):
            degree = terms[i][0]
            new_graph = axes.plot(
                lambda x: taylor_partial_sum(x, degree),
                color=term_colors[i],
                stroke_width=3
            )
            
            # Highlight the current term in the coefficient display
            self.play(
                coeff_lines[i].animate.set_color(term_colors[i]).scale(1.2),
                Transform(current_graph, new_graph),
                run_time=1.5
            )
            
            # Reset scale
            self.play(coeff_lines[i].animate.scale(1/1.2), run_time=0.5)
        
        # Final emphasis
        final_text = Text("Convergence achieved!", color=GREEN, font_size=24)
        final_text.to_edge(DOWN).shift(UP * 0.5)
        self.play(Write(final_text))
        self.wait(2)
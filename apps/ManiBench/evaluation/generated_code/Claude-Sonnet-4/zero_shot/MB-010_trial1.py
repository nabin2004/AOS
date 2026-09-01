from manim import *
import numpy as np

class TaylorSeriesAnimation(Scene):
    def construct(self):
        # Set up axes
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-2, 2, 0.5],
            x_length=10,
            y_length=6,
            axis_config={"color": GRAY}
        )
        axes_labels = axes.get_axis_labels(x_label="x", y_label="y")
        
        # Original function: sin(x)
        original_func = axes.plot(lambda x: np.sin(x), color=BLACK, stroke_width=4)
        original_label = MathTex("f(x) = \\sin(x)", color=BLACK).to_edge(UP + LEFT)
        
        # Taylor series coefficients for sin(x) around x=0
        def taylor_term(x, n):
            if n == 0:
                return 0
            elif n == 1:
                return x
            elif n == 2:
                return 0
            elif n == 3:
                return -x**3 / 6
            elif n == 4:
                return 0
            elif n == 5:
                return x**5 / 120
            elif n == 6:
                return 0
            elif n == 7:
                return -x**7 / 5040
            else:
                return 0
        
        def partial_sum(x, max_n):
            result = 0
            for i in range(max_n + 1):
                result += taylor_term(x, i)
            return result
        
        # Colors for each term
        colors = [WHITE, RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, PINK]
        
        # Create title
        title = Text("Taylor Series Expansion of sin(x)", font_size=36).to_edge(UP)
        
        # Animation starts
        self.play(Write(title))
        self.play(Create(axes), Write(axes_labels))
        self.play(Create(original_func), Write(original_label))
        self.wait(1)
        
        # Show Taylor series formula
        taylor_formula = MathTex(
            "\\sin(x) = \\sum_{n=0}^{\\infty} \\frac{(-1)^n}{(2n+1)!} x^{2n+1}",
            font_size=32
        ).to_edge(DOWN)
        self.play(Write(taylor_formula))
        self.wait(1)
        
        # Container for coefficient display
        coeff_group = VGroup()
        
        # Animate each term
        current_plots = VGroup()
        
        for n in range(8):
            # Create partial sum function
            if n == 0:
                # P₀(x) = 0 (since sin(0) = 0)
                partial_func = axes.plot(lambda x: 0, color=colors[n], stroke_width=3)
                term_text = MathTex(f"P_0(x) = 0", color=colors[n], font_size=28)
            elif n == 1:
                # P₁(x) = x
                partial_func = axes.plot(lambda x: x, color=colors[n], stroke_width=3)
                term_text = MathTex(f"P_1(x) = x", color=colors[n], font_size=28)
            elif n == 2:
                # P₂(x) = x (no x² term)
                partial_func = axes.plot(lambda x: x, color=colors[n], stroke_width=3)
                term_text = MathTex(f"P_2(x) = x", color=colors[n], font_size=28)
            elif n == 3:
                # P₃(x) = x - x³/6
                partial_func = axes.plot(lambda x: partial_sum(x, 3), color=colors[n], stroke_width=3)
                term_text = MathTex(f"P_3(x) = x - \\frac{{x^3}}{{6}}", color=colors[n], font_size=28)
            elif n == 4:
                # P₄(x) = x - x³/6 (no x⁴ term)
                partial_func = axes.plot(lambda x: partial_sum(x, 4), color=colors[n], stroke_width=3)
                term_text = MathTex(f"P_4(x) = x - \\frac{{x^3}}{{6}}", color=colors[n], font_size=28)
            elif n == 5:
                # P₅(x) = x - x³/6 + x⁵/120
                partial_func = axes.plot(lambda x: partial_sum(x, 5), color=colors[n], stroke_width=3)
                term_text = MathTex(f"P_5(x) = x - \\frac{{x^3}}{{6}} + \\frac{{x^5}}{{120}}", color=colors[n], font_size=24)
            elif n == 6:
                # P₆(x) = x - x³/6 + x⁵/120 (no x⁶ term)
                partial_func = axes.plot(lambda x: partial_sum(x, 6), color=colors[n], stroke_width=3)
                term_text = MathTex(f"P_6(x) = x - \\frac{{x^3}}{{6}} + \\frac{{x^5}}{{120}}", color=colors[n], font_size=24)
            else:
                # P₇(x) = x - x³/6 + x⁵/120 - x⁷/5040
                partial_func = axes.plot(lambda x: partial_sum(x, 7), color=colors[n], stroke_width=3)
                term_text = MathTex(f"P_7(x) = x - \\frac{{x^3}}{{6}} + \\frac{{x^5}}{{120}} - \\frac{{x^7}}{{5040}}", color=colors[n], font_size=20)
            
            # Position the term text
            term_text.to_edge(RIGHT).shift(UP * (2 - n * 0.4))
            
            # Remove previous plot and add new one
            if current_plots:
                self.play(FadeOut(current_plots[-1]))
            
            # Add current term text to group
            coeff_group.add(term_text)
            
            # Animate the new approximation
            self.play(Create(partial_func), Write(term_text))
            current_plots.add(partial_func)
            
            self.wait(0.5)
        
        # Show convergence message
        convergence_text = Text(
            "Higher-order terms improve approximation",
            font_size=32,
            color=YELLOW
        ).to_edge(DOWN).shift(UP * 0.5)
        
        self.play(FadeOut(taylor_formula))
        self.play(Write(convergence_text))
        self.wait(2)
        
        # Final comparison - show original function more prominently
        self.play(
            original_func.animate.set_stroke(width=6),
            convergence_text.animate.set_color(GREEN)
        )
        self.wait(3)
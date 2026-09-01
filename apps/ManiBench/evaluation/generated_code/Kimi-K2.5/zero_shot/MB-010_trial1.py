from manim import *
import math

class TaylorSeriesExpansion(Scene):
    def construct(self):
        # Setup axes
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 8, 1],
            x_length=10,
            y_length=6,
            axis_config={"include_numbers": True},
        ).center()
        
        # Title and labels
        title = MathTex("\\text{Taylor Series Expansion of } e^x \\text{ at } x=0").to_edge(UP)
        axes_labels = axes.get_axis_labels()
        
        self.play(Create(axes), Write(axes_labels), Write(title))
        
        # Original function in black
        original_graph = axes.plot(
            lambda x: np.exp(x), 
            x_range=[-3, 2.5],
            color=BLACK, 
            stroke_width=3
        )
        original_label = MathTex("f(x) = e^x", color=BLACK).next_to(
            axes.c2p(2, np.exp(2)), RIGHT
        )
        
        self.play(Create(original_graph), Write(original_label))
        self.wait(0.5)
        
        # Colors for each order: constant, linear, quadratic, cubic, quartic, quintic
        colors = [WHITE, RED, BLUE, GREEN, YELLOW, PURPLE]
        
        # Trackers for current approximation and formula
        current_graph = None
        current_formula = None
        
        # Generate Taylor polynomials from 0th to 5th order
        for n in range(0, 6):
            # Create polynomial function with proper closure
            def make_poly(degree):
                def poly(x, d=degree):
                    return sum(x**k / math.factorial(k) for k in range(d + 1))
                return poly
            
            poly_func = make_poly(n)
            
            # Plot the approximation
            new_graph = axes.plot(
                poly_func,
                x_range=[-3, 3],
                color=colors[n],
                stroke_width=4
            )
            
            # Build the formula with color-coded terms
            prefix = MathTex(f"P_{{{n}}}(x) = ", color=colors[n])
            
            terms_group = VGroup()
            for k in range(n + 1):
                # Create term string
                if k == 0:
                    term_str = "1"
                elif k == 1:
                    term_str = "x"
                else:
                    term_str = f"\\frac{{x^{k}}}{{{math.factorial(k)}}}"
                
                # New term gets highlight color, previous terms in gray
                term_color = colors[n] if k == n else GRAY_B
                term = MathTex(term_str, color=term_color)
                terms_group.add(term)
                
                if k < n:
                    terms_group.add(MathTex("+", color=GRAY_B))
            
            terms_group.arrange(RIGHT, buff=0.15)
            full_formula = VGroup(prefix, terms_group).arrange(RIGHT, buff=0.1)
            full_formula.scale(0.7)
            full_formula.to_edge(LEFT).shift(UP * 2.5)
            
            # Animate the approximation and formula
            if n == 0:
                self.play(Create(new_graph), Write(full_formula))
            else:
                self.play(
                    ReplacementTransform(current_graph, new_graph),
                    ReplacementTransform(current_formula, full_formula)
                )
            
            current_graph = new_graph
            current_formula = full_formula
            
            # Description text for each step
            if n == 0:
                desc = "0th order: Constant approximation P_0(x) = 1"
            elif n == 1:
                desc = "1st order: Adding linear term (red)"
            elif n == 2:
                desc = "2nd order: Adding quadratic term x²/2 (blue)"
            elif n == 3:
                desc = "3rd order: Adding cubic term x³/6 (green)"
            elif n == 4:
                desc = "4th order: Adding quartic term x⁴/24 (yellow)"
            else:
                desc = "5th order: Adding quintic term x⁵/120 (purple)"
            
            desc_text = Text(desc, font_size=24, color=colors[n])
            desc_text.to_edge(DOWN, buff=0.5)
            
            self.play(Write(desc_text))
            self.wait(1.5)
            
            if n < 5:
                self.play(FadeOut(desc_text))
        
        # Final convergence message
        convergence_text = Text(
            "Higher-order terms improve approximation", 
            font_size=28, 
            color=BLUE_D
        )
        convergence_text.to_edge(DOWN, buff=0.5)
        
        self.play(Write(convergence_text))
        self.wait(1)
        
        # Display numerical coefficients table
        coeff_title = MathTex("\\text{Taylor Coefficients } a_n = \\frac{f^{(n)}(0)}{n!}:", color=GRAY).scale(0.7)
        coeff_terms = VGroup()
        
        for k in range(6):
            coef_val = 1 / math.factorial(k)
            if coef_val == 1:
                coef_str = "1"
            else:
                coef_str = f"\\frac{{1}}{{{math.factorial(k)}}}"
            coef_tex = MathTex(f"a_{{{k}}} = {coef_str}", color=colors[k]).scale(0.6)
            coeff_terms.add(coef_tex)
        
        coeff_terms.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        coeff_group = VGroup(coeff_title, coeff_terms).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        coeff_group.to_corner(DR).shift(LEFT * 0.3 + UP * 0.5)
        
        self.play(FadeIn(coeff_group))
        
        # Highlight how the approximation converges to original
        self.play(
            current_graph.animate.set_stroke(opacity=0.6),
            original_graph.animate.set_stroke(opacity=1, width=4),
            run_time=2
        )
        
        self.wait(3)
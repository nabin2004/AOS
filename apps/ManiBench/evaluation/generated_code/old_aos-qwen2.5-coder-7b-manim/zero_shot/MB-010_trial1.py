from manim import *

class TaylorSeriesAnimation(Scene):
    def construct(self):
        # Define the function to approximate
        func = lambda x: np.sin(x)
        
        # Create axes
        ax = Axes(
            x_range=[-PI, PI, PI/2],
            y_range=[-1.5, 1.5, 0.5],
            axis_config={"color": WHITE},
        )
        ax_labels = ax.get_axis_labels(x_label="x", y_label="f(x)")
        
        # Plot the original function
        graph = ax.plot(func, color=BLACK)
        graph_label = MathTex(r"f(x) = \sin(x)").next_to(graph, UP)
        
        # Initial setup
        self.play(Create(ax), Write(ax_labels))
        self.play(Create(graph), Write(graph_label))
        self.wait()
        
        # Taylor series coefficients
        taylor_coeffs = [1, -1/6, 1/120, -1/5040]
        taylor_terms = []
        
        # Animation loop
        for i, coeff in enumerate(taylor_coeffs):
            if i == 0:
                # First term (constant)
                term = MathTex(f"P_{{0}}(x) = {coeff}").to_edge(UP)
                self.play(Write(term))
                self.wait()
                
                # Add first term to graph
                p0 = ax.plot(lambda x: coeff, color=RED)
                self.play(Create(p0))
                self.wait()
                
                # Update label
                new_term = MathTex(f"P_{{0}}(x) = {coeff}").to_edge(UP)
                self.play(Transform(term, new_term))
                self.wait()
                
            else:
                # Higher-order terms
                power = 2*i + 1
                term_str = f"P_{{{i}}}({x}) = {coeff} \\cdot \\frac{{x^{power}}}"
                new_term = MathTex(term_str).to_edge(UP)
                
                # Calculate new partial sum
                new_partial_sum = lambda x: sum([taylor_coeffs[j] * (x**(2*j+1)) / math.factorial(2*j+1) for j in range(i+1)])
                new_graph = ax.plot(new_partial_sum, color=COLORS[i%len(COLORS)])
                
                # Animate addition of new term
                self.play(Transform(term, new_term))
                self.play(Create(new_graph))
                self.wait()
                
                # Remove old graph
                self.play(FadeOut(p0))
                p0 = new_graph
                
            # Show convergence explanation
            if i >= 2:
                convergence_text = Text("Higher-order terms improve approximation", font_size=24).to_edge(DOWN)
                self.play(Write(convergence_text))
                self.wait(2)
                self.play(FadeOut(convergence_text))
            
        # Final cleanup
        self.wait()
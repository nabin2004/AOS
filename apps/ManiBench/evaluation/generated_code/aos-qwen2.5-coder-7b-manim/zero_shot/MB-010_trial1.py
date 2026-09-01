from manim import *

class TaylorSeriesAnimation(Scene):
    def construct(self):
        # Define the function to expand
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
        
        # Add labels
        self.play(Create(ax), Write(ax_labels))
        self.play(Create(graph), Write(graph_label))
        self.wait()
        
        # Taylor series expansion
        taylor_series = []
        coefficients = [1, -1/6, 1/120, -1/5040]
        colors = [RED, BLUE, GREEN, YELLOW]
        
        # Animation loop
        for i, coeff in enumerate(coefficients):
            # Construct the current polynomial
            poly = lambda x: sum([coeff * x**n / math.factorial(n) for n in range(i+1)])
            
            # Create the polynomial graph
            poly_graph = ax.plot(poly, color=colors[i])
            poly_label = MathTex(f"P_{i}(x) = {coeff:.2f} + \\cdots").to_edge(UP)
            
            # Animate the addition of the new term
            if i == 0:
                self.play(FadeIn(poly_graph), Write(poly_label))
            else:
                self.play(TransformFromCopy(prev_poly_graph, poly_graph), TransformFromCopy(prev_poly_label, poly_label))
            
            # Update previous values
            prev_poly_graph = poly_graph
            prev_poly_label = poly_label
            
            # Wait briefly
            self.wait(0.5)
        
        # Convergence explanation
        convergence_text = Text("Higher-order terms improve approximation", font_size=24).to_edge(DOWN)
        self.play(Write(convergence_text))
        self.wait(2)
        
        # Final cleanup
        self.play(*[FadeOut(mob) for mob in self.mobjects])
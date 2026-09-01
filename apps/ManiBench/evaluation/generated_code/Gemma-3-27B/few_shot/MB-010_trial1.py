from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        func = lambda x: np.sin(x)
        func_name = "sin(x)"
        x_range = [-np.pi, np.pi]
        y_range = [-1.5, 1.5]

        axes = Axes(x_range=x_range, y_range=y_range, axis_config={"include_numbers": True})
        axes.add_coordinate_labels()
        func_graph = axes.plot(func, color=BLACK)
        func_label = MathTex(f"{func_name}").next_to(func_graph, UP)

        self.play(Create(axes), Write(func_label), Create(func_graph))
        self.wait(1)

        terms = []
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE]
        coeffs = []

        # Taylor series coefficients for sin(x)
        coeffs = [0, 1, 0, -1/6, 0, 1/120]
        
        partial_sums = []
        
        def taylor_term(x, n):
            if n == 0:
                return coeffs[0]
            elif n == 1:
                return coeffs[1] * x
            elif n == 2:
                return coeffs[2] * x**2
            elif n == 3:
                return coeffs[3] * x**3
            elif n == 4:
                return coeffs[4] * x**4
            elif n == 5:
                return coeffs[5] * x**5
            else:
                return 0

        for n in range(6):
            term = axes.plot(lambda x: taylor_term(x, n), color=colors[n % len(colors)], x_range=x_range)
            terms.append(term)
            
            partial_sum = axes.plot(lambda x: sum([taylor_term(x, i) for i in range(n + 1)]), color=WHITE)
            partial_sums.append(partial_sum)

            term_label = MathTex(f"P_{n}(x) = {latex(taylor_term(0, n)) if n == 0 else latex(taylor_term(x, n)) }").next_to(term, RIGHT)
            
            self.play(Create(term), Write(term_label))
            self.play(Create(partial_sum))
            self.wait(0.5)
            
            if n > 0:
                self.play(FadeOut(term_label))

        convergence_text = Text("Higher-order terms improve approximation", font_size=24).to_edge(DOWN)
        self.play(Write(convergence_text))
        self.wait(2)
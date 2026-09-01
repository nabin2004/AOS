from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        func = sin
        func_name = "sin(x)"
        x_range = [-PI, PI, 0.1]
        n_terms = 6

        # Original function
        graph = func.plot(color=BLACK, x_range=x_range, label=func_name)
        self.play(Create(graph))

        # Taylor series coefficients
        coefficients = [
            1, 0, -1/2, 0, 1/24, 0, -1/720
        ]

        # Partial sums
        partial_sums = []
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE]

        for i in range(n_terms + 1):
            partial_sum = 0
            term_texts = []
            for j in range(i + 1):
                term = coefficients[j] * (x ** j) / math.factorial(j)
                partial_sum += term
                term_text = MathTex(f"\\frac{{{coefficients[j]}}}{{{math.factorial(j)}}}x^{j}")
                term_texts.append(term_text)

            partial_sum_func = partial_sum
            partial_sum_graph = partial_sum_func.plot(color=colors[i % len(colors)], x_range=x_range, label=f"P_{i}(x)")

            # Display terms
            term_group = VGroup(*term_texts)
            term_group.arrange(DOWN, aligned_edge=LEFT)
            term_group.next_to(graph, UP, buff=1)

            self.play(Create(partial_sum_graph))
            self.play(Write(term_group))

            partial_sums.append(partial_sum_graph)

            # Convergence text
            if i > 0:
                convergence_text = Text("Higher-order terms improve approximation")
                convergence_text.next_to(term_group, DOWN, buff=0.5)
                self.play(Write(convergence_text))

            self.wait(1)
            if i > 0:
                self.play(Unwrite(convergence_text))
            self.play(Unwrite(term_group))
            self.play(partial_sum_graph.animate.fade_out())

        self.wait(2)
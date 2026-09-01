from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        # Function to approximate
        f = lambda x: np.sin(x)
        f_name = "sin(x)"

        # Taylor series coefficients
        coefficients = [1, 0, -1/6, 0, 1/120, 0, -1/5040, 0]  # sin(x) coefficients
        terms = [f(0)]
        for i in range(1, len(coefficients)):
            terms.append(terms[-1] + coefficients[i] * (x**i))

        colors = [BLACK, RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, TEAL]

        # Plot the original function
        func_graph = f.to_graph(x_range=[-3*PI, 3*PI], color=BLACK)
        func_label = Tex(f"f(x) = {f_name}", color=BLACK).to_edge(UP)

        self.play(Create(func_graph), Write(func_label))

        # Animate the Taylor series expansion
        partial_sums = []
        coefficient_texts = []
        for i in range(len(terms)):
            p_i = lambda x: terms[i]
            p_i_graph = p_i.to_graph(x_range=[-3*PI, 3*PI], color=colors[i])
            partial_sums.append(p_i_graph)

            coefficient_text = Tex(f"P_{i}(x) = {terms[i]:.2f}", color=colors[i]).next_to(func_label, DOWN, buff=0.5 * i)
            coefficient_texts.append(coefficient_text)

            self.play(Create(p_i_graph))
            self.play(Write(coefficient_text))

            if i > 0:
                self.play(
                    Transform(partial_sums[i-1], p_i_graph),
                    Transform(coefficient_texts[i-1], coefficient_text)
                )
            else:
                self.play(Create(p_i_graph), Write(coefficient_text))

        # Convergence text
        convergence_text = Tex("Higher-order terms improve approximation", color=GREEN).to_edge(DOWN)
        self.play(Write(convergence_text))

        self.wait(3)
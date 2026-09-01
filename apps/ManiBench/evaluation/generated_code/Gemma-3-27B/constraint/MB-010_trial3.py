from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        func = lambda x: np.sin(x)
        func_graph = func.to_graph(x_range=[-3, 3], color=BLACK, weight=0.8, critical=True)
        self.play(Create(func_graph))
        self.wait(1)

        terms = []
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, TEAL, PINK]
        coefficients = [1, 0, -1/2, 0, 1/24, 0, -1/720, 0]
        
        p0 = Tex("P_0(x) = 1").scale(0.7).next_to(func_graph, UP, buff=0.5)
        p0_graph = func(0).to_graph(x_range=[-3, 3], color=RED, weight=0.9, critical=True)
        self.play(Create(p0), Create(p0_graph))
        terms.append(p0_graph)
        self.wait(1)

        for i in range(1, 8):
            term_label = Tex(f"P_{i}(x) = ").scale(0.7).next_to(p0, DOWN, buff=0.5 * i)
            term_expression = Tex(f"1 + ").scale(0.7)
            for j in range(i):
                if coefficients[j] != 0:
                    term_expression.add_text(f"({coefficients[j]} * x^{j}/{np.math.factorial(j)}) + ")
            term_expression.add_text("...")
            term_expression.next_to(term_label, RIGHT)
            
            p_graph = func(0)
            for j in range(i):
                p_graph += (coefficients[j] * x**j) / np.math.factorial(j)
            p_graph = p_graph.to_graph(x_range=[-3, 3], color=colors[i], weight=0.9, critical=True)
            
            self.play(Create(term_label), Create(term_expression), Transform(terms[-1], p_graph))
            terms.append(p_graph)
            self.wait(1)

        convergence_text = Tex("Higher-order terms improve approximation").scale(0.6).to_edge(DOWN)
        self.play(Write(convergence_text))
        self.wait(2)
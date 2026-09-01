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
            term_expression = Tex(f"{coefficients[i]}").next_to(term_label, RIGHT)
            
            if i % 2 == 1:
                term_expression.append(Tex("x").next_to(term_expression, RIGHT))
            else:
                pass
            
            term_graph = func(0)
            
            if i == 1:
                term_graph = lambda x: func(0) + coefficients[1] * x
                term_graph = term_graph.to_graph(x_range=[-3, 3], color=BLUE, weight=0.9, critical=True)
            elif i == 2:
                term_graph = lambda x: func(0) + coefficients[1] * x + coefficients[2] * (x**2)/2
                term_graph = term_graph.to_graph(x_range=[-3, 3], color=GREEN, weight=0.9, critical=True)
            elif i == 3:
                term_graph = lambda x: func(0) + coefficients[1] * x + coefficients[2] * (x**2)/2 + coefficients[3] * (x**3)/6
                term_graph = term_graph.to_graph(x_range=[-3, 3], color=YELLOW, weight=0.9, critical=True)
            elif i == 4:
                term_graph = lambda x: func(0) + coefficients[1] * x + coefficients[2] * (x**2)/2 + coefficients[3] * (x**3)/6 + coefficients[4] * (x**4)/24
                term_graph = term_graph.to_graph(x_range=[-3, 3], color=ORANGE, weight=0.9, critical=True)
            elif i == 5:
                term_graph = lambda x: func(0) + coefficients[1] * x + coefficients[2] * (x**2)/2 + coefficients[3] * (x**3)/6 + coefficients[4] * (x**4)/24 + coefficients[5] * (x**5)/120
                term_graph = term_graph.to_graph(x_range=[-3, 3], color=PURPLE, weight=0.9, critical=True)
            elif i == 6:
                term_graph = lambda x: func(0) + coefficients[1] * x + coefficients[2] * (x**2)/2 + coefficients[3] * (x**3)/6 + coefficients[4] * (x**4)/24 + coefficients[5] * (x**5)/120 + coefficients[6] * (x**6)/720
                term_graph = term_graph.to_graph(x_range=[-3, 3], color=TEAL, weight=0.9, critical=True)
            elif i == 7:
                term_graph = lambda x: func(0) + coefficients[1] * x + coefficients[2] * (x**2)/2 + coefficients[3] * (x**3)/6 + coefficients[4] * (x**4)/24 + coefficients[5] * (x**5)/120 + coefficients[6] * (x**6)/720 + coefficients[7] * (x**7)/5040
                term_graph = term_graph.to_graph(x_range=[-3, 3], color=PINK, weight=0.9, critical=True)
            
            self.play(Create(term_label), Create(term_expression), Create(term_graph))
            terms.append(term_graph)
            self.wait(1)

        convergence_text = Tex("Higher-order terms improve approximation").scale(0.7).to_edge(DOWN)
        self.play(Write(convergence_text))
        self.wait(2)
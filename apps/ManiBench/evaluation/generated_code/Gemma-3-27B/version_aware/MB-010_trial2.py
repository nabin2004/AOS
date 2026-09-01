from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        func = lambda x: np.sin(x)
        func_name = "sin(x)"
        x_range = [-PI, PI, 0.1]
        
        axes = Axes(
            x_range=x_range,
            y_range=[-1.5, 1.5],
            x_length=10,
            y_length=6,
            axis_config={"include_numbers": False},
        )
        axes.add_coordinate_labels()
        
        graph = axes.plot(func, color=BLACK)
        
        terms = []
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE]
        
        p0 = 0
        terms.append(p0)
        
        p1 = func(0) + (func(0.1) - func(0)) / 0.1 * x
        terms.append(p1)
        
        p2 = func(0) + (func(0.1) - func(0)) / 0.1 * x + ((func(0.2) - 2 * func(0.1) + func(0)) / (0.1**2)) * (x**2)
        terms.append(p2)
        
        p3 = func(0) + (func(0.1) - func(0)) / 0.1 * x + ((func(0.2) - 2 * func(0.1) + func(0)) / (0.1**2)) * (x**2) + (((func(0.3) - 3 * func(0.2) + 3 * func(0.1) - func(0)) / (0.1**3)) * (x**3))
        terms.append(p3)
        
        p4 = func(0) + (func(0.1) - func(0)) / 0.1 * x + ((func(0.2) - 2 * func(0.1) + func(0)) / (0.1**2)) * (x**2) + (((func(0.3) - 3 * func(0.2) + 3 * func(0.1) - func(0)) / (0.1**3)) * (x**3)) + ((((func(0.4) - 4 * func(0.3) + 6 * func(0.2) - 4 * func(0.1) + func(0)) / (0.1**4)) * (x**4))
        terms.append(p4)
        
        p5 = func(0) + (func(0.1) - func(0)) / 0.1 * x + ((func(0.2) - 2 * func(0.1) + func(0)) / (0.1**2)) * (x**2) + (((func(0.3) - 3 * func(0.2) + 3 * func(0.1) - func(0)) / (0.1**3)) * (x**3)) + ((((func(0.4) - 4 * func(0.3) + 6 * func(0.2) - 4 * func(0.1) + func(0)) / (0.1**4)) * (x**4)) + (((func(0.5) - 5 * func(0.4) + 10 * func(0.3) - 10 * func(0.2) + 5 * func(0.1) - func(0)) / (0.1**5)) * (x**5))
        terms.append(p5)
        
        
        term_graphs = []
        for i, term in enumerate(terms):
            term_graph = axes.plot(term, color=colors[i % len(colors)])
            term_graphs.append(term_graph)
        
        self.play(Create(axes), Create(graph))
        
        for i in range(len(terms)):
            self.play(Create(term_graphs[i]))
            
            if i < len(terms) - 1:
                self.wait(1)
        
        text = Text("Higher-order terms improve approximation", font_size=24)
        text.to_edge(DOWN)
        self.play(Write(text))
        
        self.wait(2)
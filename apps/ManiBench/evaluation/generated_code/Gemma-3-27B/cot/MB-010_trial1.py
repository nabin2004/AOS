from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        func = lambda x: np.sin(x)
        func_name = "sin(x)"
        x_range = [-PI, PI, 0.1]
        n_terms = 5

        # 1. Original function
        graph = self.plot_function(func, x_range=x_range, color=DARK_GRAY, weight=0.8)
        self.play(Create(graph))

        # 2-5. Partial sums
        partial_sums = []
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE]
        coefficients = []

        for n in range(n_terms):
            # Calculate Taylor series term
            term = self.taylor_term(func, 0, n)
            coefficients.append(term.coeff)

            # Create partial sum
            partial_sum = self.plot_function(lambda x: self.partial_sum(func, 0, n, x), x_range=x_range, color=colors[n % len(colors)], weight=0.9)
            partial_sums.append(partial_sum)

            # Label
            label = Tex(f"P_{n}(x) = {self.latex_partial_sum(func, 0, n)}", color=colors[n % len(colors)], weight=0.8)
            label.next_to(graph, UP, buff=0.5 + n * 0.3)

            # Coefficient display
            coeff_text = Tex(f"Coefficient: {term.coeff:.2f}", color=colors[n % len(colors)], weight=0.8)
            coeff_text.next_to(label, DOWN, buff=0.2)

            # Animate
            self.play(Create(partial_sum), Write(label), Write(coeff_text))
            self.wait(1)

        # 6-8. Convergence text
        convergence_text = Tex("Higher-order terms improve approximation", color=WHITE)
        convergence_text.to_edge(DOWN)
        self.play(Write(convergence_text))
        self.wait(2)

    def taylor_term(self, func, a, n):
        if n == 0:
            return TaylorTerm(func, a, n, coeff=func(a))
        else:
            # Numerical differentiation
            h = 1e-6
            derivative = (func(a + h) - func(a - h)) / (2 * h)
            if n == 1:
                return TaylorTerm(func, a, n, coeff=derivative)
            else:
                # Approximate higher-order derivatives
                return TaylorTerm(func, a, n, coeff=derivative)

    def partial_sum(self, func, a, n, x):
        sum = 0
        for i in range(n + 1):
            term = self.taylor_term(func, a, i)
            sum += term.coeff * (x - a)**i
        return sum

    def latex_partial_sum(self, func, a, n):
        latex_str = ""
        for i in range(n + 1):
            term = self.taylor_term(func, a, i)
            if i == 0:
                latex_str += f"{term.coeff:.2f}"
            else:
                latex_str += f" + {term.coeff:.2f}(x - {a})^{i}"
        return latex_str

class TaylorTerm:
    def __init__(self, func, a, n, coeff):
        self.func = func
        self.a = a
        self.n = n
        self.coeff = coeff
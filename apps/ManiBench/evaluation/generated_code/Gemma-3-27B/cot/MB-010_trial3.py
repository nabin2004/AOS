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
            partial_sum = self.plot_function(lambda x: sum([self.taylor_term(func, 0, i).func(x) for i in range(n + 1)]), x_range=x_range, color=colors[n % len(colors)], weight=0.9)
            partial_sums.append(partial_sum)

            # Label
            label = Tex(f"P_{n}(x) = {self.latex_taylor_sum(func, 0, n)}").scale(0.7).next_to(partial_sum, UP)

            # Coefficient display
            coeff_text = Tex(f"Coefficient: {term.coeff:.2f}").scale(0.6).next_to(label, DOWN)

            self.play(Create(partial_sum), Write(label), Write(coeff_text))
            self.wait(1)

        # 6-8. Convergence text
        convergence_text = Tex("Higher-order terms improve approximation").to_edge(DOWN)
        self.play(Write(convergence_text))
        self.wait(2)

    def taylor_term(self, func, a, n):
        if n == 0:
            return TaylorTerm(func, a, n)
        else:
            # Calculate the nth derivative
            def nth_derivative(f, x, n):
                if n == 0:
                    return f(x)
                else:
                    def derivative(f, x):
                        h = 1e-6
                        return (f(x + h) - f(x)) / h
                    return nth_derivative(derivative, x, n - 1)

            # Calculate the coefficient
            coeff = nth_derivative(func, a, n) / np.math.factorial(n)

            # Create the Taylor term function
            def term_func(x):
                return coeff * (x - a)**n

            return TaylorTerm(func, a, n, coeff, term_func)

    def plot_function(self, func, x_range, color, weight):
        axes = Axes(x_range=x_range, y_range=[-2, 2], x_length=10, y_length=4, axis_config={"include_numbers": False})
        graph = axes.plot(func, color=color, weight=weight)
        return graph

    def latex_taylor_sum(self, func, a, n):
        latex_string = ""
        for i in range(n + 1):
            term = self.taylor_term(func, a, i)
            if i == 0:
                latex_string += str(term.coeff)
            else:
                latex_string += f" + {term.coeff} (x - {a})^{i}"
        return latex_string

class TaylorTerm:
    def __init__(self, func, a, n, coeff=None, func_term=None):
        self.func = func
        self.a = a
        self.n = n
        self.coeff = coeff if coeff is not None else self.calculate_coefficient()
        self.func_term = func_term if func_term is not None else self.create_term_function()

    def calculate_coefficient(self):
        def nth_derivative(f, x, n):
            if n == 0:
                return f(x)
            else:
                def derivative(f, x):
                    h = 1e-6
                    return (f(x + h) - f(x)) / h
                return nth_derivative(derivative, x, n - 1)

        return nth_derivative(self.func, self.a, self.n) / np.math.factorial(self.n)

    def create_term_function(self):
        def term_func(x):
            return self.coeff * (x - self.a)**self.n
        return term_func
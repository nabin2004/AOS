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

        # 2. Taylor series terms and partial sums
        partial_sums = []
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE]
        coefficients = []

        for n in range(n_terms):
            # Calculate Taylor series term
            term = self.taylor_term(func, 0, n)
            coefficients.append(term.get_numerical_value())

            # Create partial sum
            partial_sum = self.partial_sum(partial_sums, term)
            partial_sums.append(term)

            # Color and label
            partial_sum.set_color(colors[n % len(colors)])
            label = Tex(f"P_{n}(x) = {self.latex_from_mobject(partial_sum)}", color=colors[n % len(colors)])
            label.next_to(partial_sum, UP)

            # Animate
            self.play(Create(partial_sum), Write(label))
            self.play(Transform(partial_sum, partial_sum))

            # Show convergence message
            if n == 2:
                convergence_text = Text("Higher-order terms improve approximation", color=WHITE)
                convergence_text.to_edge(DOWN)
                self.play(Write(convergence_text))

        # Display coefficients
        coefficient_text = Tex(f"Coefficients: {coefficients}", color=WHITE)
        coefficient_text.to_edge(DOWN)
        self.play(Write(coefficient_text))

        self.wait(2)

    def taylor_term(self, func, a, n):
        if n == 0:
            return Tex(str(func(a)))
        elif n == 1:
            # Approximate derivative
            h = 0.001
            derivative = (func(a + h) - func(a)) / h
            return Tex(f"{derivative}x")
        elif n == 2:
            # Approximate second derivative
            h = 0.001
            derivative2 = (func(a + h) - 2 * func(a) + func(a - h)) / (h ** 2)
            return Tex(f"{derivative2/2}x^2")
        elif n == 3:
            # Approximate third derivative
            h = 0.001
            derivative3 = (func(a + 2*h) - 2*func(a + h) + 2*func(a - h) - func(a - 2*h)) / (2 * h**3)
            return Tex(f"{derivative3/6}x^3")
        elif n == 4:
            # Approximate fourth derivative
            h = 0.001
            derivative4 = (func(a + 2*h) - 4*func(a + h) + 6*func(a) - 4*func(a - h) + func(a - 2*h)) / (h**4)
            return Tex(f"{derivative4/24}x^4")
        else:
            return Tex("...")

    def partial_sum(self, partial_sums, term):
        if not partial_sums:
            return term
        else:
            # Combine terms
            combined_term = Tex(self.latex_from_mobject(partial_sums[-1]) + " + " + self.latex_from_mobject(term))
            return combined_term

    def plot_function(self, func, x_range, color, weight):
        axes = Axes(
            x_range=x_range,
            y_range=[-2, 2],
            x_length=10,
            y_length=5,
            axis_config={"include_numbers": False},
        )
        graph = axes.plot(func, color=color, weight=weight)
        return graph

    def latex_from_mobject(self, mobject):
        if isinstance(mobject, Tex):
            return mobject.get_tex_string()
        else:
            return str(mobject)
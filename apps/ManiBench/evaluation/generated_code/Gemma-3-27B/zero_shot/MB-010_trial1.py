from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        # Function to approximate
        f = lambda x: np.sin(x)
        f_name = "sin(x)"

        # Taylor series coefficients
        coefficients = [1, 0, -1/6, 0, 1/120, 0, -1/5040, 0]  # sin(x) coefficients
        num_terms = len(coefficients)

        # Colors for each term
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, TEAL, PINK]

        # Plot the original function
        ax = Axes(
            x_range=[-3, 3],
            y_range=[-1.5, 1.5],
            x_length=10,
            y_length=6,
            axis_config={"include_numbers": False},
        )
        ax.plot(f, color=BLACK, label=f_name)
        ax.add_coordinate_labels()
        self.play(Create(ax))

        # Initial partial sum (P0)
        p0 = f(0)
        p0_line = ax.plot_line(lambda x: p0, color=RED, label="P₀(x) = 1")
        self.play(Create(p0_line))

        # Add terms progressively
        partial_sums = []
        for i in range(1, num_terms):
            term = coefficients[i] * (x ** i) / np.math.factorial(i)
            partial_sum = lambda x: f(0) + sum(
                coefficients[j] * (x ** j) / np.math.factorial(j)
                for j in range(i + 1)
            )
            
            partial_sum_line = ax.plot_line(partial_sum, color=colors[i % len(colors)], label=f"P{i}(x)")
            
            # Display coefficient
            coeff_text = Tex(f"x^{i}: {coefficients[i]} / {np.math.factorial(i)}")
            coeff_text.to_corner(UR)
            self.play(Create(partial_sum_line), Write(coeff_text))
            
            partial_sums.append(partial_sum_line)
            
            self.wait(1)
            
            if i < num_terms - 1:
                self.play(Transform(partial_sum_line, partial_sum_line))

        # Convergence text
        convergence_text = Tex("Higher-order terms improve approximation")
        convergence_text.to_corner(DL)
        self.play(Write(convergence_text))

        self.wait(3)
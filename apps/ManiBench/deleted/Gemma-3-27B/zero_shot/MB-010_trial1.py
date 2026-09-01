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
            x_range=[-3*PI, 3*PI],
            y_range=[-1.5, 1.5],
            x_length=10,
            y_length=5,
            axis_config={"include_numbers": False},
        )
        ax.plot(f, color=BLACK, label=f_name)
        ax.add_coordinate_labels()
        self.play(Create(ax))

        # Initial partial sum (P0)
        p0 = lambda x: f(0)
        p0_graph = ax.plot(p0, color=colors[0], label="P₀(x)")
        self.play(Create(p0_graph))

        # Display coefficient for P0
        coeff_text_0 = Tex(f"P₀(x) = {coefficients[0]}")
        coeff_text_0.to_corner(UR)
        self.play(Write(coeff_text_0))

        # Progressively add terms
        for i in range(1, num_terms):
            # Calculate the next partial sum
            pi = lambda x: sum(coefficients[:i+1] * (x**n) / np.math.factorial(n) for n in range(i+1))
            pi_graph = ax.plot(pi, color=colors[i % len(colors)], label=f"P{i}(x)")

            # Display coefficient for Pi
            coeff_text = Tex(f"P{i}(x) = " + " + ".join([f"{coefficients[n]}x^{n}/{np.math.factorial(n)}" for n in range(i+1)]))
            coeff_text.to_corner(UR)
            coeff_text.generate_target()
            coeff_text.target.shift(DOWN * 0.5)

            self.play(
                Create(pi_graph),
                Transform(coeff_text_0, coeff_text)
            )

            # Convergence text
            convergence_text = Tex("Higher-order terms improve approximation")
            convergence_text.to_corner(DL)
            self.play(Write(convergence_text))
            self.wait(1)
            self.play(Unwrite(convergence_text))

        # Final state
        self.play(
            Wait(2)
        )
        self.play(
            FadeOut(ax, coeff_text_0)
        )
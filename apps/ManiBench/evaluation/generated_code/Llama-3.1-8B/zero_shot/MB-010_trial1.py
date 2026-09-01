from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        # Define the function and its Taylor series expansion
        def f(x):
            return np.sin(x)

        def taylor_series(x, n):
            return np.sum([(-1)**i * x**(2*i+1) / np.factorial(2*i+1) for i in range(n)])

        # Create the axes
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-1.5, 1.5, 0.5],
            x_length=10,
            y_length=6,
            axis_config={"include_tip": False},
        )
        self.add(axes)

        # Plot the original function
        original_function = axes.plot(f, color=BLACK)
        self.add(original_function)

        # Add the Taylor series terms
        for i in range(8):
            term = axes.plot(lambda x: taylor_series(x, i+1), color=RED if i == 0 else BLUE if i == 1 else GREEN if i == 2 else YELLOW if i == 3 else ORANGE if i == 4 else PURPLE if i == 5 else PINK if i == 6 else MAROON if i == 7 else WHITE)
            self.add(term)

            # Add the numerical coefficients
            coefficient = MathTex(f"\\frac{{(-1)^{{{i}}}}}{{{2*{i}+1}}!}").next_to(term, direction=RIGHT)
            self.add(coefficient)

            # Animate the partial sum
            partial_sum = axes.plot(lambda x: taylor_series(x, i+1), color=BLACK)
            self.add(partial_sum)

            # Display the text explaining convergence
            convergence_text = Text("Higher-order terms improve approximation").next_to(partial_sum, direction=UP)
            self.add(convergence_text)

            # Wait for a bit before adding the next term
            self.wait(0.5)

        # Animate the final result
        final_result = axes.plot(f, color=BLACK)
        self.add(final_result)

        # Display the final text
        final_text = Text("Convergence achieved!").next_to(final_result, direction=UP)
        self.add(final_text)
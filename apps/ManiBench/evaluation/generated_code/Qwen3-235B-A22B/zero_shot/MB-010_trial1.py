from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        # Set up axes
        axes = Axes(
            x_range=[-2*PI, 2*PI, PI/2],
            y_range=[-2, 2, 0.5],
            axis_config={"color": WHITE},
            x_axis_config={"include_numbers": True},
            y_axis_config={"include_numbers": True}
        )
        axes_labels = axes.get_axis_labels(x_label="x", y_label="y")

        # Original function: sin(x)
        def func(x):
            return np.sin(x)

        sin_graph = axes.plot(func, color=BLACK, x_range=[-2*PI, 2*PI], stroke_width=4)
        sin_label = MathTex(r"f(x) = \sin(x)", color=BLACK).to_corner(UL).scale(0.8)

        # Taylor series of sin(x) at x=0
        def taylor_term(n):
            if n == 0:
                return lambda x: 0
            elif n == 1:
                return lambda x: x
            elif n == 2:
                return lambda x: x - (x**3) / np.math.factorial(3)
            elif n == 3:
                return lambda x: x - (x**3) / np.math.factorial(3) + (x**5) / np.math.factorial(5)
            elif n == 4:
                return lambda x: x - (x**3) / np.math.factorial(3) + (x**5) / np.math.factorial(5) - (x**7) / np.math.factorial(7)
            elif n == 5:
                return lambda x: x - (x**3) / np.math.factorial(3) + (x**5) / np.math.factorial(5) - (x**7) / np.math.factorial(7) + (x**9) / np.math.factorial(9)
            elif n == 6:
                return lambda x: x - (x**3) / np.math.factorial(3) + (x**5) / np.math.factorial(5) - (x**7) / np.math.factorial(7) + (x**9) / np.math.factorial(9) - (x**11) / np.math.factorial(11)
            elif n == 7:
                return lambda x: x - (x**3) / np.math.factorial(3) + (x**5) / np.math.factorial(5) - (x**7) / np.math.factorial(7) + (x**9) / np.math.factorial(9) - (x**11) / np.math.factorial(11) + (x**13) / np.math.factorial(13)
            else:
                return lambda x: 0

        # Colors for each added term (starting from linear term)
        term_colors = [RED, BLUE, GREEN, ORANGE, PURPLE, PINK, YELLOW]

        # Taylor series expressions
        taylor_expressions = [
            MathTex(r"P_0(x) = 0", color=WHITE),
            MathTex(r"P_1(x) = x", color=RED),
            MathTex(r"P_2(x) = x - \frac{x^3}{3!}", color=BLUE),
            MathTex(r"P_3(x) = x - \frac{x^3}{3!} + \frac{x^5}{5!}", color=GREEN),
            MathTex(r"P_4(x) = x - \frac{x^3}{3!} + \frac{x^5}{5!} - \frac{x^7}{7!}", color=ORANGE),
            MathTex(r"P_5(x) = x - \frac{x^3}{3!} + \frac{x^5}{5!} - \frac{x^7}{7!} + \frac{x^9}{9!}", color=PURPLE),
            MathTex(r"P_6(x) = x - \frac{x^3}{3!} + \frac{x^5}{5!} - \frac{x^7}{7!} + \frac{x^9}{9!} - \frac{x^{11}}{11!}", color=PINK),
            MathTex(r"P_7(x) = x - \frac{x^3}{3!} + \frac{x^5}{5!} - \frac{x^7}{7!} + \frac{x^9}{9!} - \frac{x^{11}}{11!} + \frac{x^{13}}{13!}", color=YELLOW)
        ]

        # Position expressions
        for expr in taylor_expressions:
            expr.to_corner(UR).scale(0.7)

        # Title
        title = Title("Taylor Series Expansion of $\\sin(x)$", include_underline=True)
        self.add(title)

        # Show axes and labels
        self.play(Create(axes), Write(axes_labels))
        self.wait(0.5)

        # Show original function
        self.play(Create(sin_graph), Write(sin_label))
        self.wait(1)

        # Start with P0
        current_approx = axes.plot(taylor_term(0), color=WHITE, x_range=[-2*PI, 2*PI])
        self.play(Create(current_approx), Write(taylor_expressions[0]))
        self.wait(1)

        # Add terms one by one
        for i in range(1, 8):
            new_approx = axes.plot(taylor_term(i), color=term_colors[i-1], x_range=[-2*PI, 2*PI])
            self.play(
                ReplacementTransform(current_approx, new_approx),
                Transform(taylor_expressions[0], taylor_expressions[i])
            )
            current_approx = new_approx
            self.wait(0.7)

        # Show convergence message
        convergence_text = Text("Higher-order terms improve approximation", font_size=24, color=GREEN)
        convergence_text.to_edge(DOWN)
        self.play(Write(convergence_text))
        self.wait(2)

        # Fade out everything except original function and final approximation
        self.play(
            FadeOut(taylor_expressions[0]),
            FadeOut(convergence_text),
            FadeOut(sin_label)
        )
        final_label = MathTex(r"\sin(x) \approx P_7(x)", color=GREEN).to_corner(UL).scale(0.8)
        self.play(Write(final_label))
        self.wait(2)
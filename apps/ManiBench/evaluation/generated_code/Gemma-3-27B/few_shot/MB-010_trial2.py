from manim import *

class TaylorSeriesExpansion(Scene):
    def construct(self):
        func = sin
        func_name = "sin(x)"
        x_range = [-PI, PI]
        y_range = [-1.5, 1.5]

        axes = Axes(x_range=x_range, y_range=y_range, axis_config={"include_numbers": True})
        axes.add_coordinate_labels()
        func_graph = axes.plot(func, color=BLACK)
        func_label = MathTex(f"{func_name}").next_to(func_graph, UP)

        self.play(Create(axes), Write(func_label), Create(func_graph))
        self.wait(1)

        terms = []
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE]
        coeffs = []

        # Taylor series coefficients for sin(x)
        coeffs.append(1)  # P0
        coeffs.append(0)  # P1
        coeffs.append(-1/2)  # P2
        coeffs.append(0)  # P3
        coeffs.append(1/24)  # P4
        coeffs.append(0)  # P5
        coeffs.append(-1/720)  # P6
        coeffs.append(0)  # P7

        for i in range(8):
            if i == 0:
                term = MathTex(f"P_{i}(x) = {coeffs[i]}").scale(0.7).to_corner(UL)
            else:
                term = MathTex(f"P_{i}(x) = ").scale(0.7).to_corner(UL)
                for j in range(i + 1):
                    if j == 0:
                        term.add(MathTex(f"{coeffs[j]}").scale(0.7))
                    else:
                        term.add(MathTex(f"+ {coeffs[j]}").scale(0.7))
                    if j < i:
                        term.add(MathTex(f"\\frac{{x^{i-j}}}{{\\({j}!\)}}{{}}").scale(0.7))
                    else:
                        term.add(MathTex(f"\\frac{{x^{i-j}}}{{\\({j}!\)}}{{}}").scale(0.7))

            partial_sum = axes.plot(lambda x: sum([coeffs[k] * (x**k) / factorial(k) if k <= i else 0 for k in range(i + 1)]), color=colors[i % len(colors)])
            self.play(Write(term), Create(partial_sum))
            self.wait(1)

        convergence_text = Text("Higher-order terms improve approximation", font_size=24).to_edge(DOWN)
        self.play(Write(convergence_text))
        self.wait(2)
from manim import *

class FTCAnimation(Scene):
    def construct(self):
        # Create axes
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 8, 2],
            axis_config={"color": BLUE},
        )
        axes_labels = axes.get_axis_labels(x_label="x", y_label="y")

        # Define function f(x) = x^2
        func = lambda x: x**2
        graph = axes.plot(func, color=GREEN)

        # Label for f(x)
        func_label = MathTex("f(x) = x^2").next_to(graph, UP, buff=0.2)

        # Display axes and function
        self.play(Create(axes), Write(axes_labels))
        self.play(Create(graph), Write(func_label))

        # Derivative f'(x) = 2x
        deriv_text = MathTex(r"f'(x) = 2x").to_edge(UP)
        self.play(Write(deriv_text))

        # Area under f'(x) from 0 to x
        area = axes.get_area(graph, x_range=(0, 1), color=YELLOW, opacity=0.5)
        self.play(FadeIn(area))

        # Moving vertical line from left to right
        dot = Dot(color=RED)
        dot.move_to(axes.c2p(0, 0))
        self.add(dot)

        # Animation loop for different x values
        for x in [0.5, 1, 1.5, 2]:
            new_dot = Dot(color=RED).move_to(axes.c2p(x, 0))
            self.play(Transform(dot, new_dot), run_time=0.5)

            # Update area
            new_area = axes.get_area(graph, x_range=(0, x), color=YELLOW, opacity=0.5)
            self.play(Transform(area, new_area), run_time=0.5)

            # Show equation
            eq = MathTex(r"\int_0^x f'(t) \,dt = f(x) - f(0)").to_edge(DOWN)
            self.play(Write(eq))

            # Highlight final value
            if x == 2:
                final_eq = MathTex(r"\int_0^2 f'(t) \,dt = f(2) - f(0)").to_edge(DOWN)
                self.play(Transform(eq, final_eq))

        # Final conclusion
        conclusion = Text("Fundamental Theorem of Calculus", font_size=24).to_edge(DOWN)
        self.play(Write(conclusion))
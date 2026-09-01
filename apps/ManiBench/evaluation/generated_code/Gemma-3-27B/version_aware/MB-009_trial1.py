from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define the function f(x) = x^2
        f = lambda x: x**2
        f_graph = FunctionGraph(f, x_range=[-2, 2], color=BLUE)
        f_label = Tex("f(x) = x^2", color=BLUE)

        # Define the derivative f'(x) = 2x
        f_prime = lambda x: 2*x
        f_prime_graph = FunctionGraph(f_prime, x_range=[-2, 2], color=RED)
        f_prime_label = Tex("f'(x) = 2x", color=RED)

        # Create axes for the derivative graph
        axes = Axes(
            x_range=[-2, 2],
            y_range=[-5, 5],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        axes.add_coordinate_labels()

        # Show the function and its derivative
        self.play(Create(f_graph), Write(f_label.next_to(f_graph, UP)))
        self.play(Create(f_prime_graph), Write(f_prime_label.next_to(f_prime_graph, UP)))
        self.wait(1)

        # Animate the area under f'(x) accumulating
        area = VGroup()
        x_val = 0
        dx = 0.1
        for i in range(20):
            x_val += dx
            rect = Rectangle(width=dx, height=f_prime(x_val), color=GREEN, stroke_width=0)
            rect.move_to(LEFT + DOWN + [x_val, 0, 0])
            area.add(rect)
            self.play(Create(rect))
            self.wait(0.05)

        self.wait(1)

        # Show the accumulated area (which equals f(x))
        accumulated_area_graph = FunctionGraph(f, x_range=[0, 2], color=YELLOW)
        accumulated_area_label = Tex("Accumulated Area", color=YELLOW)
        self.play(Transform(area, accumulated_area_graph), Write(accumulated_area_label.next_to(accumulated_area_graph, UP)))
        self.wait(1)

        # Demonstrate ∫₀ˣ f'(t) dt = f(x) − f(0)
        equation = MathTex(
            "\\int_{0}^{x} f'(t) \, dt = f(x) - f(0)",
        )
        self.play(Write(equation))
        self.wait(2)

        # Animate several values of x and show the correspondence
        for x in [0.5, 1, 1.5]:
            dot = Dot(axes.c2p(x, f(x)), color=PURPLE)
            dot_label = Tex(f"x = {x}", color=PURPLE).next_to(dot, RIGHT)
            self.play(Create(dot), Write(dot_label))
            self.wait(1)
            self.play(FadeOut(dot, dot_label))

        self.wait(2)
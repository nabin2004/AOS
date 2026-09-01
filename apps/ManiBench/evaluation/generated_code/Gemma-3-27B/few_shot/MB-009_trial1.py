from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define functions
        f = lambda x: 0.5 * x**2
        f_prime = lambda x: x

        # Axes
        axes_f = Axes(x_range=[-3, 3], y_range=[-1, 5], axis_config={"include_numbers": True})
        axes_f_prime = Axes(x_range=[-3, 3], y_range=[-1, 3], axis_config={"include_numbers": True})
        axes_area = Axes(x_range=[-3, 3], y_range=[-1, 5], axis_config={"include_numbers": True})

        # Plots
        graph_f = axes_f.plot(f, color=BLUE)
        graph_f_prime = axes_f_prime.plot(f_prime, color=GREEN)

        # Labels
        f_label = MathTex("f(x) = 0.5x^2").next_to(graph_f, UP)
        f_prime_label = MathTex("f'(x) = x").next_to(graph_f_prime, UP)
        integral_label = MathTex("\int_{0}^{x} f'(t) \, dt").next_to(axes_f_prime, DOWN)

        # Initial x value
        x_val = 1.5

        # Area under f'(x)
        area = axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)
        area_label = MathTex("Area").next_to(area, UP)

        # Vertical line
        vertical_line = VerticalLine(axes_f_prime.c2p(x_val, 0), axes_f_prime.c2p(x_val, f_prime(x_val)), color=RED)

        # Accumulated area graph
        accumulated_area_graph = axes_area.plot(lambda x: 0.5 * x**2, color=ORANGE)
        accumulated_area_label = MathTex("Accumulated Area").next_to(accumulated_area_graph, UP)

        # Equation
        equation = MathTex("\int_{0}^{x} f'(t) \, dt = f(x) - f(0)").next_to(accumulated_area_graph, DOWN)
        f_0_val = MathTex("f(0) = 0").next_to(equation, DOWN)
        
        # Initial scene
        self.play(Create(axes_f), Write(f_label), Create(graph_f))
        self.play(Create(axes_f_prime), Write(f_prime_label), Create(graph_f_prime))
        self.play(Create(axes_area), Write(accumulated_area_label), Create(accumulated_area_graph))
        self.wait(1)

        # Animate area accumulation
        for x in [1.5, 2.0, 2.5]:
            x_val = x
            area = axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)
            vertical_line = VerticalLine(axes_f_prime.c2p(x_val, 0), axes_f_prime.c2p(x_val, f_prime(x_val)), color=RED)
            
            self.play(
                FadeTransform(area, axes_f_prime.get_area(f_prime, x_range=[0, x_val], color=YELLOW, opacity=0.5)),
                Create(vertical_line),
                Write(integral_label),
                run_time=1
            )
            self.wait(0.5)
            
            # Show equation
            self.play(Write(equation), Write(f_0_val))
            self.wait(1)
            self.play(FadeOut(equation), FadeOut(f_0_val))
            self.play(FadeOut(area_label), FadeOut(vertical_line))
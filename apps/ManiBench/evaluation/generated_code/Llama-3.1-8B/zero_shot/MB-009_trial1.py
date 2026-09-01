from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define the function f(x) = x^2
        f = lambda x: x**2

        # Plot the function f(x)
        graph_f = Graph(f, x_min=-5, x_max=5, y_min=-5, y_max=5, color=BLUE)
        self.play(Create(graph_f))
        self.wait()

        # Plot the derivative f'(x)
        derivative_f = lambda x: 2*x
        graph_derivative_f = Graph(derivative_f, x_min=-5, x_max=5, y_min=-5, y_max=5, color=RED)
        self.play(Create(graph_derivative_f))
        self.wait()

        # Animate the area under f'(x) from 0 to x accumulating
        area = 0
        for x in np.arange(-5, 5, 0.1):
            area += derivative_f(x) * 0.1
            self.clear()
            self.play(Create(graph_f), Create(graph_derivative_f))
            self.play(MoveToTarget(graph_derivative_f, run_time=0.1))
            self.play(Create(VGroup(*[Line(np.array([x, 0, 0]), np.array([x, area, 0]), stroke_width=2) for x in np.arange(-5, 5, 0.1)])))
            self.wait(0.1)

        # Display a graph of the accumulated area (which equals f(x))
        graph_accumulated_area = Graph(lambda x: x**2, x_min=-5, x_max=5, y_min=-5, y_max=5, color=YELLOW)
        self.play(Create(graph_accumulated_area))
        self.wait()

        # Demonstrate: ∫₀ˣ f'(t) dt = f(x) − f(0)
        self.play(Write(Text("∫₀ˣ f'(t) dt = f(x) − f(0)")))
        self.wait()

        # Animate several values of x and show the correspondence
        for x in np.arange(-5, 5, 1):
            self.clear()
            self.play(Create(graph_f), Create(graph_derivative_f))
            self.play(MoveToTarget(graph_derivative_f, run_time=0.1))
            self.play(Create(VGroup(*[Line(np.array([x, 0, 0]), np.array([x, area, 0]), stroke_width=2) for x in np.arange(-5, 5, 0.1)])))
            self.play(Write(Text(f"f({x}) = {x**2}")))
            self.play(Write(Text(f"∫₀ˣ f'(t) dt = {x**2 - f(0)}")))
            self.wait(0.5)
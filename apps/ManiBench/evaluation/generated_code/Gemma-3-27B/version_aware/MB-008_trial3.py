from manim import *

class ChainRule(Scene):
    def construct(self):
        # Define functions
        g = lambda x: x**2
        f = lambda u: np.exp(u)

        # Create axes
        axes_x = Axes(x_range=[-3, 3], y_range=[-1, 10], x_length=6, y_length=4, axis_config={"include_numbers": True})
        axes_u = Axes(x_range=[-1, 10], y_range=[-1, 10], x_length=4, y_length=4, axis_config={"include_numbers": True})
        axes_y = Axes(x_range=[-1, 10], y_range=[-1, 10], x_length=4, y_length=4, axis_config={"include_numbers": True})

        # Plot functions
        graph_g = axes_x.plot(g, x_range=[-3, 3], color=BLUE)
        graph_f = axes_u.plot(f, x_range=[-1, 10], color=RED)

        # Labels
        x_label = Tex("x", color=BLUE).next_to(axes_x, DOWN)
        u_label = Tex("u", color=RED).next_to(axes_u, DOWN)
        y_label = Tex("y", color=GREEN).next_to(axes_y, DOWN)

        # Composition
        y = lambda x: f(g(x))
        graph_y = axes_x.plot(y, x_range=[-2, 2], color=GREEN)

        # Small change
        dx = 0.1
        x_val = 1
        u_val = g(x_val)
        y_val = f(u_val)

        dot_x = Dot(axes_x.coords_to_point(x_val, g(x_val)), color=BLUE)
        dot_u = Dot(axes_u.coords_to_point(u_val, 0), color=RED)
        dot_y = Dot(axes_y.coords_to_point(y_val, 0), color=GREEN)

        arrow_dx = Arrow(dot_x, dot_x + RIGHT * dx, buff=0)
        arrow_du = Arrow(dot_u, dot_u + RIGHT * 0.1, buff=0)
        arrow_dy = Arrow(dot_y, dot_y + RIGHT * 0.1, buff=0)

        # Derivative labels
        g_prime = MathTex("g'(x) = 2x").next_to(axes_x, UP)
        f_prime = MathTex("f'(u) = e^u").next_to(axes_u, UP)
        chain_rule = MathTex("\\frac{dy}{dx} = f'(g(x)) \\cdot g'(x)").next_to(axes_y, UP)

        # Initial state
        self.play(Create(axes_x), Write(x_label), Create(graph_g))
        self.play(Create(axes_u), Write(u_label), Create(graph_f))
        self.play(Create(axes_y), Write(y_label), Create(graph_y))
        self.play(Create(dot_x), Create(dot_u), Create(dot_y))
        self.play(Create(arrow_dx), Create(arrow_du), Create(arrow_dy))
        self.play(Write(g_prime), Write(f_prime), Write(chain_rule))

        self.wait(2)
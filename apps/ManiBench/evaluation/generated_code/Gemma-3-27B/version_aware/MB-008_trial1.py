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
        y_val = y(x_val)

        # Points on the curves
        point_x = Dot(axes_x.coords_to_point(x_val, g(x_val)), color=BLUE)
        point_u = Dot(axes_u.coords_to_point(u_val, y_val), color=RED)
        point_y = Dot(axes_x.coords_to_point(x_val, y_val), color=GREEN)

        # Tangent lines
        def g_prime(x):
            return 2 * x
        def f_prime(u):
            return np.exp(u)

        tangent_g = axes_x.get_tangent_line(graph_g, x_val, slope=g_prime(x_val))
        tangent_f = axes_u.get_tangent_line(graph_f, u_val, slope=f_prime(u_val))

        # Small changes du and dy
        du = g_prime(x_val) * dx
        dy = f_prime(u_val) * du

        # Arrows for changes
        arrow_dx = Arrow(axes_x.coords_to_point(x_val, 0), axes_x.coords_to_point(x_val + dx, 0), buff=0, color=BLUE)
        arrow_du = Arrow(axes_u.coords_to_point(u_val, 0), axes_u.coords_to_point(u_val + du, 0), buff=0, color=RED)
        arrow_dy = Arrow(axes_x.coords_to_point(x_val, y_val), axes_x.coords_to_point(x_val + dx, y_val + dy), buff=0, color=GREEN)

        # Equation
        equation = MathTex("y = f(g(x))", "\\frac{dy}{dx} = f'(g(x)) \\cdot g'(x)")

        # Show everything
        self.play(Create(axes_x), Create(axes_u), Create(axes_y))
        self.play(Create(graph_g), Create(graph_f), Create(graph_y))
        self.play(Write(x_label), Write(u_label), Write(y_label))
        self.play(Create(point_x), Create(point_u), Create(point_y))
        self.play(Create(tangent_g), Create(tangent_f))
        self.play(Create(arrow_dx), Create(arrow_du), Create(arrow_dy))
        self.play(Write(equation))
        self.wait(3)
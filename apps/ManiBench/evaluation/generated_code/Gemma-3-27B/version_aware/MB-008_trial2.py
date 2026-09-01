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
        y = f(g(x_label[0].get_center()[0]))
        
        # Initial point
        x_val = 1
        u_val = g(x_val)
        y_val = f(u_val)

        dot_x = Dot(axes_x.coords_to_point(x_val, 0), color=BLUE)
        dot_u = Dot(axes_u.coords_to_point(u_val, 0), color=RED)
        dot_y = Dot(axes_y.coords_to_point(y_val, 0), color=GREEN)

        # Tangent lines
        def get_tangent_line(axes, func, x_val):
            slope = (func(x_val + 0.01) - func(x_val)) / 0.01
            point = axes.coords_to_point(x_val, func(x_val))
            line = Line(point, point + Vektor(1, slope))
            return line

        tangent_g = get_tangent_line(axes_x, g, x_val)
        tangent_f = get_tangent_line(axes_u, f, u_val)

        # Small changes
        dx = 0.01
        du = tangent_g.get_slope() * dx
        dy = tangent_f.get_slope() * du

        # Arrows for changes
        arrow_dx = Arrow(dot_x.get_center(), dot_x.get_center() + RIGHT * dx, buff=0)
        arrow_du = Arrow(dot_u.get_center(), dot_u.get_center() + RIGHT * du, buff=0)
        arrow_dy = Arrow(dot_y.get_center(), dot_y.get_center() + RIGHT * dy, buff=0)

        # Derivative equation
        derivative_equation = MathTex("d/dx[f(g(x))] = f'(g(x)) \\cdot g'(x)", color=YELLOW)
        derivative_equation.to_edge(UP)

        # Show everything
        self.play(Create(axes_x), Write(x_label))
        self.play(Create(graph_g))
        self.play(Create(axes_u), Write(u_label))
        self.play(Create(graph_f))
        self.play(Create(axes_y), Write(y_label))
        self.play(Create(dot_x), Create(dot_u), Create(dot_y))
        self.play(Create(tangent_g), Create(tangent_f))
        self.play(Create(arrow_dx), Create(arrow_du), Create(arrow_dy))
        self.play(Write(derivative_equation))
        self.wait(3)
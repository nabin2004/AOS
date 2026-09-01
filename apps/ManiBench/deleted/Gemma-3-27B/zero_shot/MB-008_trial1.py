from manim import *

class ChainRuleAnimation(Scene):
    def construct(self):
        # Define functions
        g = lambda x: x**2
        f = lambda u: np.exp(u)

        # Create axes
        ax_x = Axes(x_range=[-3, 3], y_range=[-1, 10], x_length=6, y_length=4, axis_config={"include_numbers": True})
        ax_u = Axes(x_range=[-1, 5], y_range=[-1, 10], x_length=4, y_length=4, axis_config={"include_numbers": True})
        ax_y = Axes(x_range=[-1, 5], y_range=[-1, 10], x_length=4, y_length=4, axis_config={"include_numbers": True})

        # Plot functions
        graph_g = ax_x.plot(g, x_range=[-3, 3], color=BLUE)
        graph_f = ax_u.plot(f, x_range=[-1, 5], color=RED)

        # Label axes
        ax_x.add_coordinate_labels()
        ax_u.add_coordinate_labels()
        ax_y.add_coordinate_labels()

        ax_x.x_axis.label = "x"
        ax_x.y_axis.label = "u"
        ax_u.x_axis.label = "u"
        ax_u.y_axis.label = "y"
        ax_y.x_axis.label = "u"
        ax_y.y_axis.label = "y"

        # Add function labels
        g_label = Tex("g(x) = x^2").next_to(graph_g, UP)
        f_label = Tex("f(u) = e^u").next_to(graph_f, UP)

        # Show composition y = f(g(x))
        composition_label = Tex("y = f(g(x))").to_edge(UP)

        # Initial point on g(x)
        x_val = 1
        u_val = g(x_val)
        y_val = f(u_val)

        point_x = Dot(ax_x.c2p(x_val, g(x_val)), color=GREEN)
        point_u = Dot(ax_u.c2p(u_val, f(u_val)), color=GREEN)
        point_y = Dot(ax_y.c2p(u_val, f(u_val)), color=GREEN)

        # Small change dx
        dx = 0.1
        x_val_dx = x_val + dx
        u_val_dx = g(x_val_dx)
        du = u_val_dx - u_val
        dy = f(u_val_dx) - y_val

        # Derivative labels
        g_prime_label = Tex("g'(x) = 2x").next_to(g_label, DOWN)
        f_prime_label = Tex("f'(u) = e^u").next_to(f_label, DOWN)

        # Chain rule formula
        chain_rule_label = Tex("dy/dx = f'(g(x)) \\cdot g'(x)").to_edge(DOWN)

        # Group elements
        group = VGroup(ax_x, ax_u, ax_y, graph_g, graph_f, g_label, f_label, composition_label,
                      point_x, point_u, point_y, g_prime_label, f_prime_label, chain_rule_label)

        self.play(Create(ax_x), Create(ax_u), Create(ax_y))
        self.play(Create(graph_g), Create(graph_f))
        self.play(Write(g_label), Write(f_label), Write(composition_label))
        self.play(Create(point_x), Create(point_u), Create(point_y))

        # Animate the change
        arrow_dx = Arrow(ax_x.c2p(x_val, g(x_val)), ax_x.c2p(x_val_dx, g(x_val_dx)), buff=0.1, color=YELLOW)
        arrow_du = Arrow(ax_u.c2p(u_val, f(u_val)), ax_u.c2p(u_val_dx, f(u_val_dx)), buff=0.1, color=YELLOW)
        arrow_dy = Arrow(ax_y.c2p(u_val, f(u_val)), ax_y.c2p(u_val_dx, f(u_val_dx)), buff=0.1, color=YELLOW)

        self.play(Create(arrow_dx))
        self.play(Create(arrow_du))
        self.play(Create(arrow_dy))

        self.play(Write(g_prime_label), Write(f_prime_label), Write(chain_rule_label))

        self.wait(2)
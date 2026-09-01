from manim import *

class ChainRuleAnimation(Scene):
    def construct(self):
        # Define functions
        g = lambda x: x**2
        f = lambda u: np.exp(u)

        # Create axes
        ax_x = Axes(x_range=[-3, 3], y_range=[-1, 10], x_length=6, y_length=4, axis_config={"include_numbers": True})
        ax_u = Axes(x_range=[-1, 5], y_range=[-1, 10], x_length=6, y_length=4, axis_config={"include_numbers": True})
        ax_y = Axes(x_range=[-1, 5], y_range=[-1, 10], x_length=6, y_length=4, axis_config={"include_numbers": True})

        # Plot functions
        graph_g = ax_x.plot(g, x_range=[-3, 3], color=BLUE)
        graph_f = ax_u.plot(f, x_range=[-1, 5], color=RED)

        # Label axes
        ax_x.add_coordinate_labels()
        ax_u.add_coordinate_labels()
        ax_y.add_coordinate_labels()

        ax_x.set_axis_orientations(UP, RIGHT)
        ax_u.set_axis_orientations(UP, RIGHT)
        ax_y.set_axis_orientations(UP, RIGHT)

        # Add labels for functions
        text_g = Tex("g(x) = x^2").next_to(ax_x, UP)
        text_f = Tex("f(u) = e^u").next_to(ax_u, UP)
        text_composition = Tex("y = f(g(x)) = e^{x^2}").next_to(ax_y, UP)

        # Initial point on g(x)
        x_val = 1.5
        u_val = g(x_val)
        y_val = f(u_val)

        point_x = Dot(ax_x.c2p(x_val, g(x_val)), color=GREEN)
        point_u = Dot(ax_u.c2p(u_val, f(u_val)), color=GREEN)
        point_y = Dot(ax_y.c2p(y_val, 0), color=GREEN)

        # Small change dx
        dx = 0.1
        x_val_dx = x_val + dx
        u_val_dx = g(x_val_dx)
        y_val_dx = f(u_val_dx)

        # Derivative values
        g_prime_x = 2 * x_val
        f_prime_u = np.exp(u_val)

        # Show the changes
        arrow_dx = Arrow(ax_x.c2p(x_val, g(x_val)), ax_x.c2p(x_val + dx, g(x_val + dx)), buff=0, color=YELLOW)
        arrow_du = Arrow(ax_u.c2p(u_val, 0), ax_u.c2p(u_val_dx, 0), buff=0, color=YELLOW)
        arrow_dy = Arrow(ax_y.c2p(y_val, 0), ax_y.c2p(y_val_dx, 0), buff=0, color=YELLOW)

        # Derivative labels
        text_g_prime = Tex("g'(x) = 2x").next_to(ax_x, DOWN)
        text_f_prime = Tex("f'(u) = e^u").next_to(ax_u, DOWN)

        # Chain rule formula
        text_chain_rule = Tex("dy = f'(u) \\cdot g'(x) \\cdot dx").next_to(ax_y, DOWN)
        text_chain_rule_expanded = Tex("d/dx[f(g(x))] = f'(g(x)) \\cdot g'(x)").next_to(text_chain_rule, DOWN)

        # Animate
        self.play(Create(ax_x), Create(ax_u), Create(ax_y))
        self.play(Create(graph_g), Create(graph_f), Write(text_g), Write(text_f), Write(text_composition))
        self.play(Create(point_x), Create(point_u), Create(point_y))
        self.play(Create(arrow_dx), Create(arrow_du), Create(arrow_dy))
        self.play(Write(text_g_prime), Write(text_f_prime))
        self.play(Write(text_chain_rule), Write(text_chain_rule_expanded))
        self.wait(3)
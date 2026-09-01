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

        # Calculate du and dy
        u_val_dx = g(x_val_dx)
        du = u_val_dx - u_val
        dy = f(u_val_dx) - y_val

        # Derivative values
        g_prime_x = 2 * x_val
        f_prime_u = np.exp(u_val)

        # Show the changes
        arrow_dx = Arrow(ax_x.c2p(x_val, g(x_val)), ax_x.c2p(x_val_dx, g(x_val_dx)), buff=0, color=YELLOW)
        arrow_du = Arrow(ax_u.c2p(u_val, 0), ax_u.c2p(u_val + du, 0), buff=0, color=YELLOW)
        arrow_dy = Arrow(ax_y.c2p(y_val, 0), ax_y.c2p(y_val + dy, 0), buff=0, color=YELLOW)

        # Text for the chain rule
        chain_rule_text = Tex("dy = f'(u) \\cdot g'(x) \\cdot dx").next_to(ax_y, DOWN)
        chain_rule_text_values = Tex(f"dy ≈ {dy:.2f} = {f_prime_u:.2f} \\cdot {g_prime_x:.2f} \\cdot {dx:.2f}").next_to(chain_rule_text, DOWN)

        # Group elements
        group_g = VGroup(ax_x, graph_g, text_g, point_x)
        group_f = VGroup(ax_u, graph_f, text_f, point_u)
        group_y = VGroup(ax_y, text_composition, point_y)
        group_arrows = VGroup(arrow_dx, arrow_du, arrow_dy)
        group_chain_rule = VGroup(chain_rule_text, chain_rule_text_values)

        # Animation
        self.play(Create(ax_x), Create(graph_g), Write(text_g), Create(ax_u), Create(graph_f), Write(text_f), Create(ax_y), Write(text_composition))
        self.play(Create(point_x), Create(point_u), Create(point_y))
        self.wait(1)

        self.play(Create(arrow_dx))
        self.play(Create(arrow_du))
        self.play(Create(arrow_dy))
        self.wait(1)

        self.play(Write(chain_rule_text), Write(chain_rule_text_values))
        self.wait(2)

        self.play(FadeOut(group_g, group_f, group_y, group_arrows, group_chain_rule))

        # Display the derivative formula
        derivative_formula = Tex("d/dx[f(g(x))] = f'(g(x)) \\cdot g'(x)").to_edge(UP)
        self.play(Write(derivative_formula))
        self.wait(2)
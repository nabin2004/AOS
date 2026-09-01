from manim import *

class ChainRule(Scene):
    def construct(self):
        # Define functions
        g = lambda x: 0.5 * x**2
        f = lambda u: np.exp(u)

        # Create axes for g(x)
        axes_g = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 5, 1],
            x_length=5,
            y_length=3,
            axis_config={"include_numbers": True},
        )
        axes_g.add_coordinate_labels()
        graph_g = axes_g.plot(g, x_range=[-3, 3], color=BLUE)
        axes_g.label.scale(0.7)

        # Create axes for f(u)
        axes_f = Axes(
            x_range=[-2, 2, 1],
            y_range=[0, 10, 1],
            x_length=5,
            y_length=3,
            axis_config={"include_numbers": True},
        )
        axes_f.add_coordinate_labels()
        graph_f = axes_f.plot(f, x_range=[-2, 2], color=RED)
        axes_f.label.scale(0.7)

        # Labels for variables
        x_label = Tex("x", color=BLUE, weight=0.7).next_to(axes_g, DOWN)
        u_label = Tex("u = g(x)", color=RED, weight=0.7).next_to(axes_f, DOWN)
        y_label = Tex("y = f(u)", color=GREEN, weight=0.7).to_edge(UP)

        # Initial setup
        self.play(Create(axes_g), Create(graph_g), Create(axes_f), Create(graph_f))
        self.play(Write(x_label), Write(u_label), Write(y_label))

        # Small change dx
        dx = 0.5
        x_val = 1
        u_val = g(x_val)
        y_val = f(u_val)

        dx_brace = Brace(axes_g.get_x_axis(), axes_g.coords_to_point(x_val, 0), direction=axes_g.get_x_axis().direction)
        dx_brace.text = Tex(f"dx = {dx}", color=BLUE, weight=0.8).scale(0.7)
        self.play(Create(dx_brace))

        # Calculate du
        g_prime = lambda x: x
        du = g_prime(x_val) * dx

        # Visualize du
        du_brace = Brace(axes_f.get_x_axis(), axes_f.coords_to_point(u_val, 0), direction=axes_f.get_x_axis().direction)
        du_brace.text = Tex(f"du = g'(x)dx = {du:.2f}", color=RED, weight=0.8).scale(0.7)
        self.play(Transform(dx_brace, Brace(axes_g.get_x_axis(), axes_g.coords_to_point(x_val + dx, 0), direction=axes_g.get_x_axis().direction)),
                  Create(du_brace))

        # Calculate dy
        f_prime = lambda u: np.exp(u)
        dy = f_prime(u_val) * du

        # Visualize dy
        dy_brace = Brace(axes_f.get_y_axis(), axes_f.coords_to_point(0, y_val), direction=axes_f.get_y_axis().direction)
        dy_brace.text = Tex(f"dy = f'(u)du = {dy:.2f}", color=GREEN, weight=0.8).scale(0.7)
        self.play(Transform(du_brace, Brace(axes_f.get_x_axis(), axes_f.coords_to_point(u_val + du, 0), direction=axes_f.get_x_axis().direction)),
                  Create(dy_brace))

        # Chain rule formula
        chain_rule = Tex("d/dx[f(g(x))] = f'(g(x)) \\cdot g'(x)", color=YELLOW, weight=0.7)
        chain_rule.to_edge(DOWN)
        self.play(Write(chain_rule))

        self.wait(2)
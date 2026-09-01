from manim import *

class ChainRuleAnimation(Scene):
    def construct(self):
        # Define functions
        def g_func(x):
            return x**2
        def f_func(u):
            return np.exp(u)

        # Create axes for g(x)
        axes_g = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 10, 1],
            x_length=5,
            y_length=4,
            axis_config={"include_numbers": True}
        )
        axes_g.add_coordinate_labels()
        graph_g = axes_g.plot(g_func, x_range=[-3, 3], color=BLUE)
        label_g = Tex("g(x) = x^2", weight=0.7, critical=True).next_to(graph_g, UP)

        # Create axes for f(u)
        axes_f = Axes(
            x_range=[-2, 3, 1],
            y_range=[-1, 10, 1],
            x_length=5,
            y_length=4,
            axis_config={"include_numbers": True}
        )
        axes_f.add_coordinate_labels()
        graph_f = axes_f.plot(f_func, x_range=[-2, 3], color=RED)
        label_f = Tex("f(u) = e^u", weight=0.7, critical=True).next_to(graph_f, UP)

        # Display g(x) and f(u)
        self.play(Create(axes_g), Create(graph_g), Write(label_g))
        self.wait(1)
        self.play(Create(axes_f), Create(graph_f), Write(label_f))
        self.wait(1)

        # Label variables
        x_label = Tex("x", weight=0.7, critical=True).to_edge(DL)
        u_label = Tex("u = g(x)", weight=0.7, critical=True).next_to(x_label, RIGHT)
        y_label = Tex("y = f(u)", weight=0.7, critical=True).next_to(u_label, RIGHT)
        self.play(Write(x_label), Write(u_label), Write(y_label))
        self.wait(1)

        # Show dx
        dx_val = 0.2
        dx_brace = Brace(axes_g.get_x_axis(), axes_g.coords_to_point(1.5, 0), direction=DOWN)
        dx_text = Tex(f"dx = {dx_val}", weight=0.8, critical=True).next_to(dx_brace, DOWN)
        self.play(Create(dx_brace), Write(dx_text))
        self.wait(1)

        # Show du = g'(x) * dx
        g_prime_x = 2 * 1.5  # g'(x) at x=1.5
        du_val = g_prime_x * dx_val
        du_brace = Brace(axes_g.get_y_axis(), axes_g.coords_to_point(0, g_func(1.5)), direction=LEFT)
        du_text = Tex(f"du ≈ {du_val}", weight=0.8, critical=True).next_to(du_brace, LEFT)
        arrow_g = Arrow(axes_g.coords_to_point(1.5, 0), axes_g.coords_to_point(1.5, g_func(1.5)), buff=0.1)
        self.play(Create(arrow_g), Create(du_brace), Write(du_text))
        self.wait(1)

        # Show dy = f'(u) * du
        u_val = g_func(1.5)
        f_prime_u = np.exp(u_val)  # f'(u) at u=u_val
        dy_val = f_prime_u * du_val
        dy_brace = Brace(axes_f.get_y_axis(), axes_f.coords_to_point(0, f_func(u_val)), direction=LEFT)
        dy_text = Tex(f"dy ≈ {dy_val}", weight=0.8, critical=True).next_to(dy_brace, LEFT)
        arrow_f = Arrow(axes_f.coords_to_point(u_val, 0), axes_f.coords_to_point(u_val, f_func(u_val)), buff=0.1)
        self.play(Create(arrow_f), Create(dy_brace), Write(dy_text))
        self.wait(1)

        # Display chain rule formula
        chain_rule_formula = Tex("d/dx[f(g(x))] = f'(g(x)) \\cdot g'(x)", weight=0.7, critical=True).to_edge(UP)
        self.play(Write(chain_rule_formula))
        self.wait(2)

        self.play(FadeOut(axes_g, graph_g, label_g, axes_f, graph_f, label_f, x_label, u_label, y_label, dx_brace, dx_text, du_brace, du_text, arrow_g, dy_brace, dy_text, arrow_f, chain_rule_formula))
        self.wait()
from manim import *

class ChainRule(Scene):
    def construct(self):
        # 1. Define functions
        g = lambda x: 0.5 * x**2
        f = lambda u: np.exp(u)

        # 2. Create axes for g(x)
        axes_g = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 5, 1],
            x_length=5,
            y_length=3,
            axis_config={"include_numbers": True}
        )
        axes_g.add_coordinate_labels()
        graph_g = axes_g.plot(g, x_range=[-3, 3], color=BLUE)
        axes_g.add(graph_g)
        axes_g.shift(LEFT * 2)
        self.play(Create(axes_g), Create(graph_g))

        # 3. Create axes for f(u)
        axes_f = Axes(
            x_range=[-2, 3, 1],
            y_range=[0, 10, 1],
            x_length=5,
            y_length=3,
            axis_config={"include_numbers": True}
        )
        axes_f.add_coordinate_labels()
        graph_f = axes_f.plot(f, x_range=[-2, 3], color=RED)
        axes_f.add(graph_f)
        axes_f.shift(RIGHT * 2)
        self.play(Create(axes_f), Create(graph_f))

        # 4. Label variables
        x_label = Tex("x", color=BLUE, weight=0.7).next_to(axes_g, DOWN)
        u_label = Tex("u = g(x)", color=RED, weight=0.7).next_to(axes_f, DOWN)
        y_label = Tex("y = f(u)", color=GREEN, weight=0.7).to_edge(UP)

        self.play(Write(x_label), Write(u_label), Write(y_label))

        # 5. Show dx
        dx = 0.2
        x_val = 1
        u_val = g(x_val)
        
        dx_brace = Brace(axes_g.c2p(x_val, 0), DOWN, color=YELLOW, weight=0.8)
        dx_text = Tex(f"dx = {dx}", color=YELLOW, weight=0.8).next_to(dx_brace, DOWN)
        self.play(Create(dx_brace), Write(dx_text))

        # 6. Propagate dx to du
        g_prime_x = self.get_derivative(g, x_val)
        du = g_prime_x * dx
        
        du_brace = Brace(axes_f.c2p(u_val, 0), DOWN, color=ORANGE, weight=0.8)
        du_text = Tex(f"du = g'(x)dx = {g_prime_x:.2f} * {dx:.2f} = {du:.2f}", color=ORANGE, weight=0.8).next_to(du_brace, DOWN)
        self.play(Create(du_brace), Write(du_text))

        # 7. Propagate du to dy
        f_prime_u = self.get_derivative(f, u_val)
        dy = f_prime_u * du

        dy_brace = Brace(y_label, DOWN, color=PURPLE, weight=0.8)
        dy_text = Tex(f"dy = f'(u)du = {f_prime_u:.2f} * {du:.2f} = {dy:.2f}", color=PURPLE, weight=0.8).next_to(dy_brace, DOWN)
        self.play(Create(dy_brace), Write(dy_text))

        # 8. Display chain rule formula
        chain_rule_formula = MathTex(
            "\\frac{d}{dx} f(g(x)) = f'(g(x)) \\cdot g'(x)",
            color=GRAY,
            weight=0.7
        ).to_edge(DOWN)
        self.play(Write(chain_rule_formula))

        self.wait(2)

    def get_derivative(self, func, x):
        h = 1e-6
        return (func(x + h) - func(x)) / h
from manim import *

class ChainRule(Scene):
    def construct(self):
        # Define functions
        g = lambda x: 0.5 * x**2  # Parabola
        f = lambda u: np.exp(u)  # Exponential
        
        # Define axes
        axes_x = Axes(x_range=[-3, 3], y_range=[0, 5], axis_config={"include_numbers": True})
        axes_u = Axes(x_range=[-1, 5], y_range=[0, 10], axis_config={"include_numbers": True})
        axes_y = Axes(x_range=[-3, 3], y_range=[0, 10], axis_config={"include_numbers": True})

        # Plot functions
        graph_g = axes_x.plot(g, color=BLUE)
        graph_f = axes_u.plot(f, color=GREEN)

        # Initial point
        x_val = 2
        u_val = g(x_val)
        y_val = f(u_val)

        dot_x = Dot(axes_x.c2p(x_val, g(x_val)), color=RED)
        dot_u = Dot(axes_u.c2p(u_val, f(u_val)), color=RED)
        dot_y = Dot(axes_y.c2p(x_val, y_val), color=RED)

        # Labels
        label_x = Text("x", font_size=24).next_to(axes_x.get_x_axis(), DOWN)
        label_u = Text("u", font_size=24).next_to(axes_u.get_x_axis(), DOWN)
        label_y = Text("y", font_size=24).next_to(axes_y.get_x_axis(), DOWN)
        
        label_g = MathTex("g(x) = 0.5x^2").to_corner(UL)
        label_f = MathTex("f(u) = e^u").to_corner(UR)
        label_comp = MathTex("y = f(g(x))").to_corner(UR + DOWN * 0.5)

        # Derivative labels
        label_g_prime = MathTex("g'(x) = x").next_to(label_g, DOWN)
        label_f_prime = MathTex("f'(u) = e^u").next_to(label_f, DOWN)
        label_chain_rule = MathTex("\\frac{dy}{dx} = f'(g(x)) \\cdot g'(x)").to_corner(DL)

        # Small change
        dx = 0.1

        # Animate initial setup
        self.play(Create(axes_x), Write(label_x), Create(graph_g), Write(label_g),
                  Create(axes_u), Write(label_u), Create(graph_f), Write(label_f),
                  Create(axes_y), Write(label_y), Write(label_comp))
        self.play(FadeIn(dot_x), FadeIn(dot_u), FadeIn(dot_y))
        self.wait(1)

        # Animate change in x
        dot_x_new = Dot(axes_x.c2p(x_val + dx, g(x_val + dx)), color=RED)
        arrow_dx = Arrow(dot_x.get_center(), dot_x_new.get_center(), buff=0.1, color=YELLOW)
        self.play(Create(arrow_dx), run_time=0.5)
        self.play(dot_x.animate.move_to(dot_x_new.get_center()), run_time=0.5)
        self.wait(0.5)

        # Change in u
        du = g(x_val + dx) - u_val
        dot_u_new = Dot(axes_u.c2p(u_val + du, f(u_val + du)), color=RED)
        arrow_du = Arrow(dot_u.get_center(), dot_u_new.get_center(), buff=0.1, color=ORANGE)
        self.play(Create(arrow_du), run_time=0.5)
        self.play(dot_u.animate.move_to(dot_u_new.get_center()), run_time=0.5)
        self.wait(0.5)

        # Change in y
        dy = f(u_val + du) - y_val
        dot_y_new = Dot(axes_y.c2p(x_val + dx, y_val + dy), color=RED)
        arrow_dy = Arrow(dot_y.get_center(), dot_y_new.get_center(), buff=0.1, color=GREEN)
        self.play(Create(arrow_dy), run_time=0.5)
        self.play(dot_y.animate.move_to(dot_y_new.get_center()), run_time=0.5)
        self.wait(0.5)

        # Display derivatives
        self.play(Write(label_g_prime), Write(label_f_prime), Write(label_chain_rule))
        self.wait(2)
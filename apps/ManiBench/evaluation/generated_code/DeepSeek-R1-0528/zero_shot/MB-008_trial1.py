from manim import *

class ChainRule(Scene):
    def construct(self):
        # Configuration
        axes_config = {
            "x_range": [-1, 3, 1],
            "y_range": [-1, 3, 1],
            "axis_config": {"color": BLUE},
        }
        dot_radius = 0.08
        tangent_length = 0.5
        dx_value = 0.3
        x0 = 1.0

        # Define functions and derivatives
        g = lambda x: x**2
        g_prime = lambda x: 2*x
        f = lambda u: np.sin(u)
        f_prime = lambda u: np.cos(u)

        # Calculate values
        u0 = g(x0)
        y0 = f(u0)
        du = g_prime(x0) * dx_value
        dy = f_prime(u0) * du

        # Create axes
        top_axes = Axes(
            x_range=[-0.5, 2.5, 0.5],
            y_range=[-0.5, 3.5, 0.5],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True}
        ).shift(UP)
        top_axes_labels = top_axes.get_axis_labels(x_label="x", y_label="u")
        top_title = Tex("$g(x) = x^2$", font_size=36).next_to(top_axes, UP)

        bottom_axes = Axes(
            x_range=[-0.5, 3.5, 0.5],
            y_range=[-1.5, 1.5, 0.5],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True}
        ).shift(DOWN)
        bottom_axes_labels = bottom_axes.get_axis_labels(x_label="u", y_label="y")
        bottom_title = Tex("$f(u) = \\sin(u)$", font_size=36).next_to(bottom_axes, UP)

        # Plot functions
        g_graph = top_axes.plot(g, color=GREEN)
        f_graph = bottom_axes.plot(f, color=YELLOW)

        # Points and lines
        x0_dot = Dot(top_axes.c2p(x0, 0), color=RED, radius=dot_radius)
        x0_label = MathTex("x_0", font_size=24).next_to(x0_dot, DOWN, buff=0.1)
        
        u0_dot_top = Dot(top_axes.c2p(x0, u0), color=RED, radius=dot_radius)
        u0_label_top = MathTex("u_0", font_size=24).next_to(u0_dot_top, UR, buff=0.1)
        
        u0_dot_bottom = Dot(bottom_axes.c2p(u0, 0), color=RED, radius=dot_radius)
        u0_label_bottom = MathTex("u_0", font_size=24).next_to(u0_dot_bottom, DOWN, buff=0.1)
        
        y0_dot = Dot(bottom_axes.c2p(u0, y0), color=RED, radius=dot_radius)
        y0_label = MathTex("y_0", font_size=24).next_to(y0_dot, UL, buff=0.1)
        
        # Connection lines
        v_line_top = DashedLine(
            start=top_axes.c2p(x0, 0),
            end=top_axes.c2p(x0, u0),
            color=RED
        )
        h_line_bottom = DashedLine(
            start=bottom_axes.c2p(0, y0),
            end=bottom_axes.c2p(u0, y0),
            color=RED
        )
        connector = DashedLine(
            start=top_axes.c2p(x0, u0),
            end=bottom_axes.c2p(u0, 0),
            color=GRAY
        )

        # Tangent lines
        top_tangent = top_axes.get_secant_slope_group(
            x=x0, graph=g_graph, dx=0.001,
            dx_line_color=YELLOW,
            dy_line_color=YELLOW,
            dx_label=None,
            dy_label=None,
            secant_line_color=RED,
            secant_line_length=tangent_length
        )
        bottom_tangent = bottom_axes.get_secant_slope_group(
            x=u0, graph=f_graph, dx=0.001,
            dx_line_color=YELLOW,
            dy_line_color=YELLOW,
            dx_label=None,
            dy_label=None,
            secant_line_color=RED,
            secant_line_length=tangent_length
        )

        # dx, du, dy segments
        dx_line = Line(
            start=top_axes.c2p(x0, 0),
            end=top_axes.c2p(x0+dx_value, 0),
            color=PURPLE,
            stroke_width=4
        )
        dx_label = MathTex("dx", font_size=24).next_to(dx_line, DOWN, buff=0.1)
        
        du_line = Line(
            start=top_axes.c2p(x0+dx_value, g(x0)),
            end=top_axes.c2p(x0+dx_value, g(x0)+du),
            color=ORANGE,
            stroke_width=4
        )
        du_label = MathTex("du", font_size=24).next_to(du_line, RIGHT, buff=0.1)
        
        dy_line = Line(
            start=bottom_axes.c2p(u0+du, f(u0)),
            end=bottom_axes.c2p(u0+du, f(u0)+dy),
            color=MAROON,
            stroke_width=4
        )
        dy_label = MathTex("dy", font_size=24).next_to(dy_line, LEFT, buff=0.1)

        # Derivative equations
        chain_rule_eq = MathTex(
            r"\frac{dy}{dx} = f'(u) \cdot g'(x) \cdot dx",
            font_size=36
        ).to_edge(DOWN)
        derivative_eq = MathTex(
            r"\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)",
            font_size=36
        ).to_edge(DOWN)

        # Animation sequence
        self.play(
            Create(top_axes),
            Create(bottom_axes),
            Write(top_axes_labels),
            Write(bottom_axes_labels),
            Write(top_title),
            Write(bottom_title),
            run_time=2
        )
        self.play(
            Create(g_graph),
            Create(f_graph),
            run_time=2
        )
        self.wait()
        
        # Show initial points
        self.play(
            Create(x0_dot),
            Write(x0_label),
            run_time=1
        )
        self.play(
            Create(v_line_top),
            Create(u0_dot_top),
            Write(u0_label_top),
            run_time=1
        )
        self.play(
            Create(connector),
            Create(u0_dot_bottom),
            Write(u0_label_bottom),
            run_time=1
        )
        self.play(
            Create(h_line_bottom),
            Create(y0_dot),
            Write(y0_label),
            run_time=1
        )
        self.wait()
        
        # Show tangents
        self.play(Create(top_tangent), run_time=1.5)
        self.play(Create(bottom_tangent), run_time=1.5)
        self.wait()
        
        # Show dx
        self.play(Create(dx_line), Write(dx_label), run_time=1)
        self.wait()
        
        # Show du
        self.play(Create(du_line), Write(du_label), run_time=1)
        self.wait()
        
        # Show dy
        self.play(Create(dy_line), Write(dy_label), run_time=1)
        self.wait()
        
        # Show chain rule equation
        self.play(Write(chain_rule_eq), run_time=2)
        self.wait(2)
        self.play(Transform(chain_rule_eq, derivative_eq), run_time=2)
        self.wait(3)
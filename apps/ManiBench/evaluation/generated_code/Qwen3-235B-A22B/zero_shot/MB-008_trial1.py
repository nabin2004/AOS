from manim import *

class ChainRuleAnimation(Scene):
    def construct(self):
        # Set up axes
        x_axis = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 9, 2],
            axis_config={"color": BLUE},
            x_axis_config={"include_numbers": True},
            y_axis_config={"include_numbers": True}
        ).scale(0.8).shift(LEFT * 3)
        x_labels = x_axis.get_axis_labels(x_label="x", y_label="u = g(x)")

        u_axis = Axes(
            x_range=[-1, 9, 2],
            y_range=[-1, 9, 2],
            axis_config={"color": GREEN},
            x_axis_config={"include_numbers": True},
            y_axis_config={"include_numbers": True}
        ).scale(0.8)
        u_labels = u_axis.get_axis_labels(x_label="u", y_label="y = f(u)")

        y_axis = Axes(
            x_range=[-1, 9, 2],
            y_range=[-1, 9, 2],
            axis_config={"color": RED},
            x_axis_config={"include_numbers": True},
            y_axis_config={"include_numbers": True}
        ).scale(0.8).shift(RIGHT * 3)
        y_labels = y_axis.get_axis_labels(x_label="y", y_label="dy/dx")

        # Position the axes
        u_axis.move_to(x_axis.get_right() + RIGHT * 1.5)
        y_axis.move_to(u_axis.get_right() + RIGHT * 1.5)

        # Labels for functions
        g_label = MathTex("g(x)", color=BLUE).next_to(x_axis, UP)
        f_label = MathTex("f(u)", color=GREEN).next_to(u_axis, UP)
        comp_label = MathTex("y = f(g(x))", color=RED).next_to(y_axis, UP)

        # Define functions
        # g(x) = x^2 + 1 (parabola)
        g_graph = x_axis.plot(lambda x: x**2 + 1, color=BLUE, x_range=[-2.5, 2.5])
        
        # f(u) = sqrt(u) (simple smooth function)
        f_graph = u_axis.plot(lambda u: np.sqrt(u), color=GREEN, x_range=[0.01, 8.5])
        
        # Composite function f(g(x)) = sqrt(x^2 + 1)
        comp_graph = y_axis.plot(lambda x: np.sqrt(x**2 + 1), color=RED, x_range=[-2.5, 2.5])

        # Point of interest
        x0 = 1.5
        u0 = x0**2 + 1
        y0 = np.sqrt(u0)

        # Dots for current values
        dot_x = Dot(color=YELLOW).move_to(x_axis.c2p(x0, u0))
        dot_u = Dot(color=YELLOW).move_to(u_axis.c2p(u0, y0))
        dot_y = Dot(color=YELLOW).move_to(y_axis.c2p(x0, y0))

        # Labels for points
        x_dot_label = MathTex("x", color=YELLOW).next_to(dot_x, UP)
        u_dot_label = MathTex("u = g(x)", color=YELLOW).next_to(dot_u, UP)
        y_dot_label = MathTex("y = f(g(x))", color=YELLOW).next_to(dot_y, UP)

        # Small change dx
        dx = 0.3
        x1 = x0 + dx
        u1 = x1**2 + 1
        y1 = np.sqrt(u1)

        # Dots for perturbed values
        dot_x1 = Dot(color=TEAL).move_to(x_axis.c2p(x1, u1))
        dot_u1 = Dot(color=TEAL).move_to(u_axis.c2p(u1, np.sqrt(u1)))
        dot_y1 = Dot(color=TEAL).move_to(y_axis.c2p(x1, y1))

        # Labels for perturbed points
        dx_label = MathTex("dx", color=TEAL).next_to(
            x_axis.c2p((x0 + x1)/2, u0), DOWN
        )
        du_label = MathTex("du", color=TEAL).next_to(
            u_axis.c2p((u0 + u1)/2, y0), DOWN
        )
        dy_label = MathTex("dy", color=TEAL).next_to(
            y_axis.c2p((x0 + x1)/2, y0), DOWN
        )

        # Derivative lines (tangents)
        g_prime = 2 * x0  # derivative of x^2 + 1 at x0
        f_prime = 0.5 / np.sqrt(u0)  # derivative of sqrt(u) at u0

        # Tangent line for g at x0
        g_tangent = x_axis.get_secant_slope_group(
            x=x0, graph=g_graph, dx=dx, dx_line_color=TEAL,
            dy_line_color=TEAL, secant_line_color=BLUE
        )

        # Tangent line for f at u0
        f_tangent = u_axis.get_secant_slope_group(
            x=u0, graph=f_graph, dx=(u1 - u0), dx_line_color=TEAL,
            dy_line_color=TEAL, secant_line_color=GREEN
        )

        # Chain rule formula
        chain_rule = MathTex(
            r"\frac{dy}{dx} = \frac{dy}{du} \cdot \frac{du}{dx}",
            color=WHITE
        ).scale(0.8).to_edge(UP)

        chain_rule_detail = MathTex(
            r"= f'(g(x)) \cdot g'(x)",
            color=WHITE
        ).scale(0.8).next_to(chain_rule, DOWN)

        # Numerical values
        values = VGroup(
            MathTex(rf"g'({x0}) = {g_prime:.1f}", color=BLUE),
            MathTex(rf"f'({u0:.1f}) = {f_prime:.2f}", color=GREEN),
            MathTex(rf"dy/dx \approx {((y1 - y0) / dx):.2f}", color=RED)
        ).arrange(DOWN).scale(0.7).to_edge(DOWN)

        # Animations
        self.play(
            Create(x_axis), Write(x_labels), Write(g_label)
        )
        self.play(
            Create(u_axis), Write(u_labels), Write(f_label)
        )
        self.play(
            Create(y_axis), Write(y_labels), Write(comp_label)
        )
        self.wait(1)

        self.play(
            Create(g_graph), Create(f_graph), Create(comp_graph)
        )
        self.wait(1)

        self.play(
            FadeIn(dot_x), Write(x_dot_label),
            FadeIn(dot_u), Write(u_dot_label),
            FadeIn(dot_y), Write(y_dot_label)
        )
        self.wait(1)

        # Show dx
        self.play(
            FadeIn(dot_x1),
            Write(dx_label)
        )
        self.play(
            Create(g_tangent)
        )
        self.wait(1)

        # Show du
        self.play(
            FadeIn(dot_u1),
            Write(du_label)
        )
        self.play(
            Create(f_tangent)
        )
        self.wait(1)

        # Show dy
        self.play(
            FadeIn(dot_y1),
            Write(dy_label)
        )
        self.wait(1)

        # Show chain rule formula
        self.play(
            Write(chain_rule),
            Write(chain_rule_detail)
        )
        self.wait(1)

        # Show derivative values
        self.play(
            Write(values)
        )
        self.wait(2)

        # Highlight the chain rule
        final_explanation = MathTex(
            r"\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)",
            color=YELLOW
        ).move_to(chain_rule.get_center())

        self.play(
            ReplacementTransform(VGroup(chain_rule, chain_rule_detail), final_explanation),
            values.animate.shift(UP * 0.5)
        )
        self.wait(2)

        # Fade out everything except the final formula
        self.play(
            FadeOut(VGroup(
                x_axis, u_axis, y_axis, x_labels, u_labels, y_labels,
                g_label, f_label, comp_label,
                g_graph, f_graph, comp_graph,
                dot_x, dot_u, dot_y, dot_x1, dot_u1, dot_y1,
                x_dot_label, u_dot_label, y_dot_label,
                dx_label, du_label, dy_label,
                g_tangent, f_tangent, values
            ))
        )
        self.wait(1)

        self.play(
            final_explanation.animate.scale(1.2).set_color(YELLOW)
        )
        self.wait(2)
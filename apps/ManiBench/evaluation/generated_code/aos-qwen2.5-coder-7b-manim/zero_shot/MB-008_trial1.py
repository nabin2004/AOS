from manim import *

class ChainRuleVisualization(Scene):
    def construct(self):
        # Create axes for g(x) and f(u)
        ax_g = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 2],
            axis_config={"color": BLUE},
        ).shift(LEFT * 3 + DOWN * 0.5)
        
        ax_f = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 2],
            axis_config={"color": GREEN},
        ).shift(RIGHT * 3 + DOWN * 0.5)

        # Add labels for axes
        label_g = MathTex("g(x)").next_to(ax_g.get_x_axis(), RIGHT)
        label_f = MathTex("f(u)").next_to(ax_f.get_x_axis(), RIGHT)

        # Define g(x) as a parabola
        g_func = lambda x: x**2
        graph_g = ax_g.plot(g_func, color=BLUE)
        dot_g = Dot(point=ax_g.c2p(1, g_func(1)), color=YELLOW)
        label_dot_g = MathTex("x").next_to(dot_g, UP)

        # Define f(u) as an exponential curve
        f_func = lambda u: np.exp(u)
        graph_f = ax_f.plot(f_func, color=GREEN)
        dot_f = Dot(point=ax_f.c2p(1, f_func(1)), color=YELLOW)
        label_dot_f = MathTex("y").next_to(dot_f, UP)

        # Composition equation
        comp_eq = MathTex(r"y = f(g(x))").to_edge(UP)

        # Derivative equations
        deriv_eq = MathTex(r"\frac{dy}{dx} = f'(g(x)) \cdot g'(x)").to_edge(DOWN)

        # Animation sequence
        self.play(Create(ax_g), Write(label_g))
        self.play(Create(graph_g), FadeIn(dot_g), Write(label_dot_g))
        self.wait()

        self.play(Create(ax_f), Write(label_f))
        self.play(Create(graph_f), FadeIn(dot_f), Write(label_dot_f))
        self.wait()

        self.play(Write(comp_eq))
        self.wait()

        # Show derivative steps
        step1 = MathTex(r"\Delta y = f(g(x+\Delta x)) - f(g(x))")
        step2 = MathTex(r"\approx f'(g(x)) \cdot g'(x) \cdot \Delta x")
        step3 = MathTex(r"\frac{\Delta y}{\Delta x} \approx f'(g(x)) \cdot g'(x)")

        self.play(ReplacementTransform(step1.copy(), step2))
        self.wait()
        self.play(Transform(step2, step3))
        self.wait()

        # Show final derivative equation
        self.play(ReplacementTransform(step3, deriv_eq))
        self.wait()
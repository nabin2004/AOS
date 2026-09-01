from manim import *

class ChainRuleVisualization(Scene):
    def construct(self):
        # Title
        title = Text("The Chain Rule", font_size=36)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

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

        # Labels for axes
        label_x = MathTex("x").next_to(ax_g.x_axis, RIGHT)
        label_u = MathTex("u").next_to(ax_g.y_axis, UP)
        label_y = MathTex("y").next_to(ax_f.y_axis, UP)

        # Function g(x) = u = x^2
        func_g = ax_g.plot(lambda x: x**2, color=BLUE)
        label_g = MathTex("g(x) = u = x^2").next_to(ax_g, UP)

        # Function f(u) = y = e^u
        func_f = ax_f.plot(lambda u: np.exp(u), color=GREEN)
        label_f = MathTex("f(u) = y = e^u").next_to(ax_f, UP)

        # Composition y = f(g(x)) = e^(x^2)
        comp_label = MathTex("y = f(g(x)) = e^{x^2}").to_edge(UP)

        # Add everything to scene
        self.play(Create(ax_g), Write(label_x), Write(label_u))
        self.play(Create(func_g), Write(label_g))
        self.wait(1)

        self.play(Create(ax_f), Write(label_y))
        self.play(Create(func_f), Write(label_f))
        self.play(Write(comp_label))
        self.wait(1)

        # Show input x and output y
        dot_x = Dot(ax_g.c2p(1, 1), color=YELLOW)
        label_dx = MathTex(r"\Delta x").next_to(dot_x, DOWN)
        line_x = Line(ax_g.c2p(0, 0), ax_g.c2p(1, 1), color=YELLOW)

        dot_u = Dot(ax_g.c2p(1, 1), color=YELLOW)
        label_du = MathTex(r"\Delta u").next_to(dot_u, RIGHT)
        line_u = Line(ax_g.c2p(1, 0), ax_g.c2p(1, 1), color=YELLOW)

        dot_y = Dot(ax_f.c2p(1, np.exp(1)), color=YELLOW)
        label_dy = MathTex(r"\Delta y").next_to(dot_y, UP)
        line_y = Line(ax_f.c2p(1, 1), ax_f.c2p(1, np.exp(1)), color=YELLOW)

        # Animation showing propagation of change
        self.play(Create(line_x), FadeIn(dot_x), Write(label_dx))
        self.wait(0.5)
        self.play(TransformFromCopy(dot_x, dot_u), TransformFromCopy(line_x, line_u), Write(label_du))
        self.wait(0.5)
        self.play(TransformFromCopy(dot_u, dot_y), TransformFromCopy(line_u, line_y), Write(label_dy))
        self.wait(1)

        # Clear screen and show derivative formula
        self.play(
            FadeOut(ax_g),
            FadeOut(ax_f),
            FadeOut(label_x),
            FadeOut(label_y),
            FadeOut(label_u),
            FadeOut(label_v),
            FadeOut(label_w),
            FadeOut(label_z),
            FadeOut(label_dx),
            FadeOut(label_du),
            FadeOut(label_dy),
            FadeOut(line_x),
            FadeOut(line_u),
            FadeOut(line_y),
            FadeOut(dot_x),
            FadeOut(dot_u),
            FadeOut(dot_y),
            FadeOut(comp_label),
            FadeOut(label_g),
            FadeOut(label_f),
        )

        # Derivative formula
        formula = MathTex(r"\frac{dy}{dx} = \frac{df}{du} \cdot \frac{dg}{dx}")
        formula.next_to(VGroup(label_dx, label_du, label_dy), DOWN, buff=1)

        # Simplified version
        simplified = MathTex(r"\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)")
        simplified.next_to(formula, DOWN, buff=0.5)

        self.play(Write(formula))
        self.wait(1)
        self.play(Write(simplified))
        self.wait(2)
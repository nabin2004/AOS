from manim import *

class ChainRuleAnimation(Scene):
    def construct(self):
        # Title
        title = Text("Chain Rule: Function Composition", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        
        # Set up coordinate systems
        axes1 = Axes(
            x_range=[-2, 2, 1],
            y_range=[-1, 3, 1],
            x_length=4,
            y_length=3,
            axis_config={"color": BLUE}
        ).shift(LEFT * 4 + DOWN * 0.5)
        
        axes2 = Axes(
            x_range=[-1, 3, 1],
            y_range=[-2, 2, 1],
            x_length=4,
            y_length=3,
            axis_config={"color": GREEN}
        ).shift(RIGHT * 4 + DOWN * 0.5)
        
        # Labels for axes
        g_label = MathTex("g(x) = x^2", color=BLUE).next_to(axes1, UP)
        f_label = MathTex("f(u) = \\sin(u)", color=GREEN).next_to(axes2, UP)
        
        x_label1 = MathTex("x", color=BLUE).next_to(axes1.x_axis, DOWN)
        u_label1 = MathTex("u", color=BLUE).next_to(axes1.y_axis, LEFT)
        u_label2 = MathTex("u", color=GREEN).next_to(axes2.x_axis, DOWN)
        y_label = MathTex("y", color=GREEN).next_to(axes2.y_axis, LEFT)
        
        self.play(
            Create(axes1), Create(axes2),
            Write(g_label), Write(f_label),
            Write(x_label1), Write(u_label1), Write(u_label2), Write(y_label)
        )
        self.wait(1)
        
        # Define functions
        def g_func(x):
            return x**2
        
        def f_func(u):
            return np.sin(u)
        
        def g_prime(x):
            return 2*x
        
        def f_prime(u):
            return np.cos(u)
        
        # Plot functions
        g_graph = axes1.plot(g_func, x_range=[-1.5, 1.5], color=BLUE)
        f_graph = axes2.plot(f_func, x_range=[0, 2.5], color=GREEN)
        
        self.play(Create(g_graph), Create(f_graph))
        self.wait(1)
        
        # Choose a point
        x_val = 1.0
        u_val = g_func(x_val)
        y_val = f_func(u_val)
        
        # Mark points
        x_dot = Dot(axes1.c2p(x_val, 0), color=RED)
        u_dot_on_g = Dot(axes1.c2p(x_val, u_val), color=RED)
        u_dot_on_f = Dot(axes2.c2p(u_val, 0), color=RED)
        y_dot = Dot(axes2.c2p(u_val, y_val), color=RED)
        
        # Labels for points
        x_text = MathTex("x", color=RED).next_to(x_dot, DOWN)
        u_text1 = MathTex("u = g(x)", color=RED).next_to(u_dot_on_g, RIGHT)
        u_text2 = MathTex("u", color=RED).next_to(u_dot_on_f, DOWN)
        y_text = MathTex("y = f(u)", color=RED).next_to(y_dot, RIGHT)
        
        self.play(
            Create(x_dot), Create(u_dot_on_g), Create(u_dot_on_f), Create(y_dot),
            Write(x_text), Write(u_text1), Write(u_text2), Write(y_text)
        )
        self.wait(1)
        
        # Show mapping arrows
        arrow1 = Arrow(
            axes1.c2p(x_val, 0), axes1.c2p(x_val, u_val),
            color=YELLOW, buff=0.1
        )
        arrow2 = Arrow(
            axes2.c2p(u_val, 0), axes2.c2p(u_val, y_val),
            color=YELLOW, buff=0.1
        )
        
        self.play(Create(arrow1), Create(arrow2))
        self.wait(1)
        
        # Show small changes
        dx = 0.3
        x_new = x_val + dx
        u_new = g_func(x_new)
        y_new = f_func(u_new)
        du = u_new - u_val
        dy = y_new - y_val
        
        # New points for changes
        x_dot_new = Dot(axes1.c2p(x_new, 0), color=ORANGE)
        u_dot_new_on_g = Dot(axes1.c2p(x_new, u_new), color=ORANGE)
        u_dot_new_on_f = Dot(axes2.c2p(u_new, 0), color=ORANGE)
        y_dot_new = Dot(axes2.c2p(u_new, y_new), color=ORANGE)
        
        # Change indicators
        dx_brace = BraceBetweenPoints(
            axes1.c2p(x_val, -0.2), axes1.c2p(x_new, -0.2),
            direction=DOWN, color=ORANGE
        )
        dx_label = MathTex("dx", color=ORANGE).next_to(dx_brace, DOWN)
        
        du_brace = BraceBetweenPoints(
            axes1.c2p(x_val + 0.1, u_val), axes1.c2p(x_val + 0.1, u_new),
            direction=RIGHT, color=ORANGE
        )
        du_label = MathTex("du", color=ORANGE).next_to(du_brace, RIGHT)
        
        dy_brace = BraceBetweenPoints(
            axes2.c2p(u_val + 0.1, y_val), axes2.c2p(u_val + 0.1, y_new),
            direction=RIGHT, color=ORANGE
        )
        dy_label = MathTex("dy", color=ORANGE).next_to(dy_brace, RIGHT)
        
        self.play(
            Create(x_dot_new), Create(u_dot_new_on_g),
            Create(u_dot_new_on_f), Create(y_dot_new)
        )
        self.wait(0.5)
        
        self.play(
            Create(dx_brace), Write(dx_label),
            Create(du_brace), Write(du_label),
            Create(dy_brace), Write(dy_label)
        )
        self.wait(2)
        
        # Show tangent lines and derivatives
        tangent_g = axes1.plot(
            lambda x: u_val + g_prime(x_val) * (x - x_val),
            x_range=[x_val - 0.5, x_val + 0.5],
            color=PURPLE
        )
        
        tangent_f = axes2.plot(
            lambda u: y_val + f_prime(u_val) * (u - u_val),
            x_range=[u_val - 0.5, u_val + 0.5],
            color=PURPLE
        )
        
        g_prime_label = MathTex("g'(x) = 2x", color=PURPLE).move_to(LEFT * 4 + UP * 2)
        f_prime_label = MathTex("f'(u) = \\cos(u)", color=PURPLE).move_to(RIGHT * 4 + UP * 2)
        
        self.play(
            Create(tangent_g), Create(tangent_f),
            Write(g_prime_label), Write(f_prime_label)
        )
        self.wait(2)
        
        # Clear some elements for the final formula
        self.play(
            FadeOut(VGroup(
                x_dot, u_dot_on_g, u_dot_on_f, y_dot,
                x_dot_new, u_dot_new_on_g, u_dot_new_on_f, y_dot_new,
                x_text, u_text1, u_text2, y_text,
                arrow1, arrow2, tangent_g, tangent_f,
                dx_brace, dx_label, du_brace, du_label, dy_brace, dy_label
            ))
        )
        
        # Show the chain rule formula
        chain_rule = MathTex(
            "\\frac{dy}{dx} = \\frac{dy}{du} \\cdot \\frac{du}{dx} = f'(g(x)) \\cdot g'(x)",
            font_size=48
        ).move_to(DOWN * 2.5)
        
        # Step by step derivation
        step1 = MathTex("du = g'(x) \\cdot dx", color=BLUE).move_to(DOWN * 1.5 + LEFT * 2)
        step2 = MathTex("dy = f'(u) \\cdot du", color=GREEN).move_to(DOWN * 1.5 + RIGHT * 2)
        step3 = MathTex("dy = f'(u) \\cdot g'(x) \\cdot dx", color=YELLOW).move_to(DOWN * 2)
        
        self.play(Write(step1))
        self.wait(1)
        self.play(Write(step2))
        self.wait(1)
        self.play(Write(step3))
        self.wait(1)
        self.play(Transform(step3, chain_rule))
        self.wait(2)
        
        # Final emphasis
        box = SurroundingRectangle(chain_rule, color=YELLOW, buff=0.2)
        self.play(Create(box))
        self.wait(3)
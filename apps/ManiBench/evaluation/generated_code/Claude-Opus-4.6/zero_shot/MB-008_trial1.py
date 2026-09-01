from manim import *

class ChainRuleAnimation(Scene):
    def construct(self):
        # Title
        title = Text("The Chain Rule", font_size=48, color=YELLOW)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # Step 1: Show the two functions and composition
        func_g = MathTex(r"g(x) = x^2", font_size=36, color=BLUE)
        func_f = MathTex(r"f(u) = \sin(u)", font_size=36, color=GREEN)
        func_comp = MathTex(r"y = f(g(x)) = \sin(x^2)", font_size=36, color=RED)

        func_group = VGroup(func_g, func_f, func_comp).arrange(DOWN, buff=0.4)
        func_group.next_to(title, DOWN, buff=0.5)

        self.play(Write(func_g))
        self.wait(0.3)
        self.play(Write(func_f))
        self.wait(0.3)
        self.play(Write(func_comp))
        self.wait(1)

        # Fade out and move to mapping visualization
        self.play(
            FadeOut(func_group),
            title.animate.scale(0.7).to_corner(UL)
        )

        # Step 2 & 3: Visualize the mappings with axes
        # Create three number lines representing x, u, y domains
        x_line = NumberLine(x_range=[-2, 2, 1], length=3, include_numbers=True, font_size=20)
        u_line = NumberLine(x_range=[-1, 4, 1], length=3, include_numbers=True, font_size=20)
        y_line = NumberLine(x_range=[-1.5, 1.5, 1], length=3, include_numbers=True, font_size=20)

        x_label = MathTex("x", font_size=36, color=WHITE)
        u_label = MathTex("u", font_size=36, color=BLUE)
        y_label = MathTex("y", font_size=36, color=GREEN)

        x_line.move_to(LEFT * 4.5 + UP * 1)
        u_line.move_to(UP * 1)
        y_line.move_to(RIGHT * 4.5 + UP * 1)

        x_label.next_to(x_line, UP, buff=0.3)
        u_label.next_to(u_line, UP, buff=0.3)
        y_label.next_to(y_line, UP, buff=0.3)

        g_arrow = Arrow(x_line.get_right(), u_line.get_left(), buff=0.2, color=BLUE)
        f_arrow = Arrow(u_line.get_right(), y_line.get_left(), buff=0.2, color=GREEN)

        g_label_arrow = MathTex(r"g(x)=x^2", font_size=24, color=BLUE).next_to(g_arrow, UP, buff=0.1)
        f_label_arrow = MathTex(r"f(u)=\sin(u)", font_size=24, color=GREEN).next_to(f_arrow, UP, buff=0.1)

        self.play(
            Create(x_line), Write(x_label),
            Create(u_line), Write(u_label),
            Create(y_line), Write(y_label),
        )
        self.play(
            GrowArrow(g_arrow), Write(g_label_arrow),
            GrowArrow(f_arrow), Write(f_label_arrow),
        )
        self.wait(0.5)

        # Show a specific point x0 = 1
        x0 = 1.0
        u0 = x0 ** 2  # u0 = 1
        y0 = np.sin(u0)  # y0 = sin(1)

        x_dot = Dot(x_line.n2p(x0), color=YELLOW, radius=0.08)
        u_dot = Dot(u_line.n2p(u0), color=YELLOW, radius=0.08)
        y_dot = Dot(y_line.n2p(y0), color=YELLOW, radius=0.08)

        x_val = MathTex(r"x_0=1", font_size=24, color=YELLOW).next_to(x_dot, DOWN, buff=0.3)
        u_val = MathTex(r"u_0=1", font_size=24, color=YELLOW).next_to(u_dot, DOWN, buff=0.3)
        y_val = MathTex(r"y_0=\sin(1)", font_size=24, color=YELLOW).next_to(y_dot, DOWN, buff=0.3)

        self.play(FadeIn(x_dot), Write(x_val))
        self.wait(0.3)

        # Animate propagation: x -> u
        moving_dot1 = x_dot.copy().set_color(ORANGE)
        self.play(
            moving_dot1.animate.move_to(u_line.n2p(u0)),
            run_time=1
        )
        self.play(FadeIn(u_dot), Write(u_val), FadeOut(moving_dot1))
        self.wait(0.3)

        # Animate propagation: u -> y
        moving_dot2 = u_dot.copy().set_color(ORANGE)
        self.play(
            moving_dot2.animate.move_to(y_line.n2p(y0)),
            run_time=1
        )
        self.play(FadeIn(y_dot), Write(y_val), FadeOut(moving_dot2))
        self.wait(1)

        # Step 4: Show small changes dx, du, dy
        # Clear the mapping visualization
        mapping_group = VGroup(
            x_line, u_line, y_line, x_label, u_label, y_label,
            g_arrow, f_arrow, g_label_arrow, f_label_arrow,
            x_dot, u_dot, y_dot, x_val, u_val, y_val
        )
        self.play(FadeOut(mapping_group))

        # Now show the chain rule with graphs
        # Left graph: g(x) = x^2
        ax_g = Axes(
            x_range=[-0.5, 2, 0.5],
            y_range=[-0.5, 3.5, 1],
            x_length=4,
            y_length=3,
            axis_config={"include_numbers": True, "font_size": 20},
            tips=False,
        ).shift(LEFT * 3.2 + DOWN * 0.5)

        ax_g_label = MathTex(r"u = g(x) = x^2", font_size=28, color=BLUE).next_to(ax_g, UP, buff=0.2)

        graph_g = ax_g.plot(lambda x: x**2, x_range=[0, 1.8], color=BLUE)

        # Right graph: f(u) = sin(u)
        ax_f = Axes(
            x_range=[-0.5, 3.5, 1],
            y_range=[-1.2, 1.2, 0.5],
            x_length=4,
            y_length=3,
            axis_config={"include_numbers": True, "font_size": 20},
            tips=False,
        ).shift(RIGHT * 3.2 + DOWN * 0.5)

        ax_f_label = MathTex(r"y = f(u) = \sin(u)", font_size=28, color=GREEN).next_to(ax_f, UP, buff=0.2)

        graph_f = ax_f.plot(lambda u: np.sin(u), x_range=[0, 3.2], color=GREEN)

        self.play(
            Create(ax_g), Write(ax_g_label), Create(graph_g),
            Create(ax_f), Write(ax_f_label), Create(graph_f),
        )
        self.wait(0.5)

        # Mark point x0 = 1 on g
        x0 = 1.0
        u0 = x0**2
        y0 = np.sin(u0)

        dot_g = Dot(ax_g.c2p(x0, u0), color=YELLOW, radius=0.06)
        dot_f = Dot(ax_f.c2p(u0, y0), color=YELLOW, radius=0.06)

        self.play(FadeIn(dot_g), FadeIn(dot_f))

        # Show dx on g graph
        dx = 0.4
        x1 = x0 + dx
        u1 = x1**2
        du = u1 - u0
        y1 = np.sin(u1)
        dy = y1 - y0

        # dx bracket on x-axis of g
        dx_line = Line(
            ax_g.c2p(x0, 0), ax_g.c2p(x1, 0),
            color=RED, stroke_width=4
        )
        dx_label = MathTex(r"\Delta x", font_size=24, color=RED).next_to(dx_line, DOWN, buff=0.15)

        # Vertical line showing du
        du_line_g = Line(
            ax_g.c2p(x1, u0), ax_g.c2p(x1, u1),
            color=ORANGE, stroke_width=4
        )
        du_label_g = MathTex(r"\Delta u", font_size=24, color=ORANGE).next_to(du_line_g, RIGHT, buff=0.1)

        # Tangent line at x0 on g
        g_prime_x0 = 2 * x0  # derivative of x^2 at x0=1
        tangent_g = ax_g.plot(
            lambda x: u0 + g_prime_x0 * (x - x0),
            x_range=[x0 - 0.5, x0 + 0.7],
            color=YELLOW_A,
            stroke_width=2,
        )

        self.play(Create(dx_line), Write(dx_label))
        self.wait(0.3)

        # Show the new point on g
        dot_g_new = Dot(ax_g.c2p(x1, u1), color=ORANGE, radius=0.06)
        self.play(FadeIn(dot_g_new))
        self.play(Create(du_line_g), Write(du_label_g))
        self.play(Create(tangent_g))
        self.wait(0.5)

        # g'(x0) label
        g_prime_label = MathTex(r"g'(1) = 2", font_size=24, color=YELLOW_A)
        g_prime_label.next_to(tangent_g, UP + RIGHT, buff=0.1)
        self.play(Write(g_prime_label))

        # Now show du on f graph
        du_line_f = Line(
            ax_f.c2p(u0, 0), ax_f.c2p(u1, 0),
            color=ORANGE, stroke_width=4
        )
        du_label_f = MathTex(r"\Delta u", font_size=24, color=ORANGE).next_to(du_line_f, DOWN, buff=0.15)

        # dy on f graph
        dy_line_f = Line(
            ax_f.c2p(u1, y0), ax_f.c2p(u1, y1),
            color=PURPLE, stroke_width=4
        )
        dy_label_f = MathTex(r"\Delta y", font_size=24, color=PURPLE).next_to(dy_line_f, RIGHT, buff=0.1)

        # Tangent line at u0 on f
        f_prime_u0 = np.cos(u0)  # derivative of sin(u) at u0=1
        tangent_f = ax_f.plot(
            lambda u: y0 + f_prime_u0 * (u - u0),
            x_range=[u0 - 0.5, u0 + 1.2],
            color=YELLOW_A,
            stroke_width=2,
        )

        dot_f_new = Dot(ax_f.c2p(u1, y1), color=PURPLE, radius=0.06)

        # Animate propagation: du from g to f
        propagation_arrow = CurvedArrow(
            du_label_g.get_right() + RIGHT * 0.1,
            du_label_f.get_left() + LEFT * 0.1,
            angle=-TAU / 6,
            color=ORANGE
        )

        self.play(Create(propagation_arrow), run_time=0.8)
        self.play(Create(du_line_f), Write(du_label_f))
        self.play(FadeIn(dot_f_new))
        self.play(Create(dy_line_f), Write(dy_label_f))
        self.play(Create(tangent_f))

        f_prime_label = MathTex(r"f'(1) = \cos(1)", font_size=24, color=YELLOW_A)
        f_prime_label.next_to(tangent_f, UP + RIGHT, buff=0.1)
        self.play(Write(f_prime_label))
        self.wait(1)

        # Step 5: Show the chain of changes
        chain_eq = MathTex(
            r"\Delta y",
            r"\approx",
            r"f'(u_0)",
            r"\cdot",
            r"\Delta u",
            r"\approx",
            r"f'(u_0)",
            r"\cdot",
            r"g'(x_0)",
            r"\cdot",
            r"\Delta x",
            font_size=30
        )
        chain_eq.to_edge(DOWN, buff=0.6)
        chain_eq[0].set_color(PURPLE)
        chain_eq[2].set_color(GREEN)
        chain_eq[4].set_color(ORANGE)
        chain_eq[6].set_color(GREEN)
        chain_eq[8].set_color(BLUE)
        chain_eq[10].set_color(RED)

        box = SurroundingRectangle(chain_eq, color=WHITE, buff=0.15)

        self.play(Write(chain_eq), Create(box))
        self.wait(2)

        # Step 6: Clear and show final chain rule formula
        all_objects = VGroup(
            ax_g, ax_g_label, graph_g, dot_g, dot_g_new,
            dx_line, dx_label, du_line_g, du_label_g,
            tangent_g, g_prime_label,
            ax_f, ax_f_label, graph_f, dot_f, dot_f_new,
            du_line_f, du_label_f, dy_line_f, dy_label_f,
            tangent_f, f_prime_label,
            propagation_arrow, chain_eq, box
        )

        self.play(FadeOut(all_objects), run_time=1)

        # Final chain rule display
        final_title = Text("The Chain Rule", font_size=48, color=YELLOW)
        final_title.to_edge(UP, buff=0.8)

        # Build up the chain rule step by step
        step1 = MathTex(
            r"\frac{dy}{dx} = \frac{dy}{du} \cdot \frac{du}{dx}",
            font_size=44
        )
        step1.next_to(final_title, DOWN, buff=0.8)

        step2 = MathTex(
            r"\frac{d}{dx}\left[f(g(x))\right] = f'(g(x)) \cdot g'(x)",
            font_size=44,
            color=GOLD
        )
        step2.next_to(step1, DOWN, buff=0.8)

        # Specific example
        step3 = MathTex(
            r"\frac{d}{dx}\left[\sin(x^2)\right] = \cos(x^2) \cdot 2x",
            font_size=40,
            color=TEAL
        )
        step3.next_to(step2, DOWN, buff=0.8)

        final_box = SurroundingRectangle(step2, color=GOLD, buff=0.2, stroke_width=3)

        self.play(FadeOut(title))
        self.play(Write(final_title))
        self.wait(0.3)

        self.play(Write(step1))
        self.wait(1)

        self.play(Write(step2))
        self.play(Create(final_box))
        self.wait(1)

        self.play(Write(step3))
        self.wait(0.5)

        # Highlight the components
        # f'(g(x)) part
        brace_f = Brace(step2[0][18:26], DOWN, color=GREEN)
        brace_f_label = MathTex(r"\text{outer derivative}", font_size=24, color=GREEN)
        brace_f_label.next_to(brace_f, DOWN, buff=0.1)

        brace_g = Brace(step2[0][27:31], DOWN, color=BLUE)
        brace_g_label = MathTex(r"\text{inner derivative}", font_size=24, color=BLUE)
        brace_g_label.next_to(brace_g, DOWN, buff=0.1)

        self.play(GrowFromCenter(brace_f), Write(brace_f_label))
        self.wait(0.5)
        self.play(GrowFromCenter(brace_g), Write(brace_g_label))
        self.wait(0.5)

        # Animate the "chain" visual
        chain_text = Text("Changes propagate through the chain!", font_size=28, color=YELLOW)
        chain_text.to_edge(DOWN, buff=0.4)

        # Create chain links
        links = VGroup()
        labels_chain = [r"dx", r"\xrightarrow{g'}", r"du", r"\xrightarrow{f'}", r"dy"]
        colors_chain = [RED, BLUE, ORANGE, GREEN, PURPLE]

        for i, (lab, col) in enumerate(zip(labels_chain, colors_chain)):
            t = MathTex(lab, font_size=36, color=col)
            links.add(t)

        links.arrange(RIGHT, buff=0.4)
        links.next_to(chain_text, UP, buff=0.3)

        self.play(Write(chain_text))

        for link in links:
            self.play(FadeIn(link, shift=RIGHT * 0.3), run_time=0.5)

        self.wait(2)

        # Final flash
        flash_rect = SurroundingRectangle(
            VGroup(step2, final_box), color=YELLOW, buff=0.3, stroke_width=5
        )
        self.play(
            Create(flash_rect),
            flash_rect.animate.set_stroke(opacity=0),
            run_time=1.5
        )
        self.wait(1)
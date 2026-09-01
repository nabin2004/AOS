from manim import *

class ChainRuleVisualization(Scene):
    def construct(self):
        # Define the functions
        # g(x) = x^2 (Parabola)
        # f(u) = sin(u) + 2 (Sine wave shifted up for visibility)
        g = lambda x: x**2
        f = lambda u: np.sin(u) + 2
        
        # Derivatives
        g_prime = lambda x: 2*x
        f_prime = lambda u: np.cos(u)

        # Configuration
        x_val = 1.0
        dx_val = 0.15
        
        u_val = g(x_val)
        y_val = f(u_val)
        
        du_val = g_prime(x_val) * dx_val
        dy_val = f_prime(u_val) * du_val

        # --- Axes Setup ---
        # Left Axes: x -> u (Function g)
        axes_g = Axes(
            x_range=[-0.5, 2.5, 1],
            y_range=[-0.5, 4.5, 1],
            x_length=4,
            y_length=4,
            axis_config={"include_tip": True, "numbers_to_exclude": [0]},
        ).shift(LEFT * 3.5)
        
        labels_g = VGroup(
            axes_g.get_x_axis_label("x"),
            axes_g.get_y_axis_label("u")
        )
        
        graph_g = axes_g.plot(g, x_range=[0, 2.1], color=BLUE)
        label_g = MathTex("u = g(x) = x^2").next_to(axes_g, UP).set_color(BLUE)

        # Right Axes: u -> y (Function f)
        axes_f = Axes(
            x_range=[-0.5, 4.5, 1],
            y_range=[-0.5, 3.5, 1],
            x_length=4,
            y_length=4,
            axis_config={"include_tip": True, "numbers_to_exclude": [0]},
        ).shift(RIGHT * 3.5)
        
        labels_f = VGroup(
            axes_f.get_x_axis_label("u"),
            axes_f.get_y_axis_label("y")
        )
        
        graph_f = axes_f.plot(f, x_range=[0, 4.1], color=GREEN)
        label_f = MathTex("y = f(u) = \\sin(u) + 2").next_to(axes_f, UP).set_color(GREEN)

        # Title
        title = Text("The Chain Rule: Visualizing Composition", font_size=36)
        title.to_edge(UP)

        # --- Initial Points and Lines ---
        # On Graph G
        point_x = axes_g.c2p(x_val, 0)
        point_x_dx = axes_g.c2p(x_val + dx_val, 0)
        
        point_u_start = axes_g.c2p(x_val, u_val)
        point_u_end = axes_g.c2p(x_val + dx_val, u_val + du_val)
        
        line_dx = DashedLine(point_x, point_x_dx, color=WHITE)
        label_dx = MathTex("dx").scale(0.7).next_to(line_dx, DOWN, buff=0.1)
        
        line_du_g = DashedLine(
            axes_g.c2p(x_val, u_val), 
            axes_g.c2p(x_val, u_val + du_val), 
            color=YELLOW
        )
        # Horizontal projection to show du magnitude on u-axis visually? 
        # Let's draw the vertical change directly on the curve
        secant_g = DashedLine(point_u_start, point_u_end, color=RED, stroke_width=2)
        
        # On Graph F
        # Note: The input to f is u. So we move from u to u+du
        point_u_in = axes_f.c2p(u_val, 0)
        point_u_in_du = axes_f.c2p(u_val + du_val, 0)
        
        point_y_start = axes_f.c2p(u_val, y_val)
        point_y_end = axes_f.c2p(u_val + du_val, y_val + dy_val)
        
        line_du_f = DashedLine(point_u_in, point_u_in_du, color=YELLOW)
        label_du_input = MathTex("du").scale(0.7).next_to(line_du_f, DOWN, buff=0.1)
        
        secant_f = DashedLine(point_y_start, point_y_end, color=RED, stroke_width=2)
        
        line_dy = DashedLine(
            axes_f.c2p(u_val, y_val),
            axes_f.c2p(u_val, y_val + dy_val),
            color=ORANGE
        )
        label_dy = MathTex("dy").scale(0.7).next_to(line_dy, RIGHT, buff=0.1)

        # Connecting the two graphs (Visual flow)
        # We will animate dots moving, but let's prepare the labels
        formula_intro = MathTex("y = f(g(x))", font_size=40)
        formula_intro.next_to(title, DOWN)

        # --- Animation Sequence ---
        
        # 1. Setup Scene
        self.play(Write(title), Write(formula_intro))
        self.play(
            Create(axes_g), Write(labels_g), Create(graph_g), Write(label_g),
            Create(axes_f), Write(labels_f), Create(graph_f), Write(label_f),
            run_time=2
        )
        self.wait(1)

        # 2. Show initial point x
        dot_x = Dot(point_x, color=WHITE)
        dot_u_graph = Dot(point_u_start, color=BLUE)
        dot_y_graph = Dot(point_y_start, color=GREEN)
        
        label_x_val = MathTex(f"x={x_val}").scale(0.6).next_to(point_x, DOWN)
        label_u_val = MathTex(f"u={u_val:.1f}").scale(0.6).next_to(point_u_start, LEFT)
        label_y_val = MathTex(f"y={y_val:.1f}").scale(0.6).next_to(point_y_start, RIGHT)

        self.play(
            Create(dot_x), Write(label_x_val),
            Create(dot_u_graph), Write(label_u_val),
            Create(dot_y_graph), Write(label_y_val)
        )
        self.wait(1)

        # 3. Introduce dx
        self.play(Create(line_dx), Write(label_dx))
        
        # 4. Propagate to u (via g)
        # Show the change in u on the first graph
        target_u_point = axes_g.c2p(x_val + dx_val, g(x_val + dx_val))
        
        # Animate the movement along g
        path_g = VMobject()
        path_g.set_points_as_corners([point_u_start, point_u_end]) # Approx linear for small dx visualization
        
        self.play(
            Create(secant_g),
            dot_u_graph.animate.move_to(point_u_end),
            run_time=1.5
        )
        
        # Highlight du on the first graph (vertical change)
        # We draw a vertical line from old u height to new u height at the NEW x position?
        # Standard calculus viz: du ≈ g'(x)dx. 
        # Let's show the vertical segment representing du at the new x position
        vert_du_g = DashedLine(
            axes_g.c2p(x_val + dx_val, u_val),
            axes_g.c2p(x_val + dx_val, u_val + du_val), # Linear approx height
            color=YELLOW
        )
        label_du_g = MathTex("du").scale(0.7).next_to(vert_du_g, RIGHT, buff=0.1)
        
        self.play(
            Create(vert_du_g), Write(label_du_g),
            run_time=1
        )

        # 5. Transfer du to the second graph
        # Show du as the input change on the u-axis of graph f
        self.play(
            Create(line_du_f), Write(label_du_input),
            run_time=1
        )
        
        # 6. Propagate to y (via f)
        self.play(
            Create(secant_f),
            dot_y_graph.animate.move_to(point_y_end),
            run_time=1.5
        )
        
        # Highlight dy
        self.play(
            Create(line_dy), Write(label_dy),
            run_time=1
        )
        
        self.wait(1)

        # 7. Show the Formula
        # Clear some clutter or shift things to make room? 
        # Let's bring up the formula at the bottom
        chain_rule_formula = MathTex(
            r"\frac{dy}{dx}", "=", r"\frac{dy}{du}", r"\cdot", r"\frac{du}{dx}"
        ).scale(1.2)
        chain_rule_formula.to_edge(DOWN)
        
        # Breakdown
        breakdown = VGroup(
            MathTex(r"\frac{du}{dx}", "=", "g'(x)").scale(0.8),
            MathTex(r"\frac{dy}{du}", "=", "f'(u)").scale(0.8),
            MathTex(r"\therefore \frac{dy}{dx}", "=", "f'(g(x))", r"\cdot", "g'(x)").scale(0.8)
        ).arrange(DOWN, aligned_edge=LEFT)
        breakdown.next_to(chain_rule_formula, UP, buff=0.5)

        self.play(Write(chain_rule_formula))
        self.play(Write(breakdown))
        
        # Highlight the connection
        box = SurroundingRectangle(breakdown[2], color=WHITE, buff=0.2)
        self.play(Create(box))
        
        self.wait(2)

        # Final cleanup/freeze
        self.play(
            FadeOut(box),
            FadeOut(line_dx), FadeOut(label_dx),
            FadeOut(secant_g), FadeOut(vert_du_g), FadeOut(label_du_g),
            FadeOut(line_du_f), FadeOut(label_du_input),
            FadeOut(secant_f), FadeOut(line_dy), FadeOut(label_dy),
            run_time=1
        )
        
        final_text = Text("Chain Rule Visualized", font_size=30, color=YELLOW)
        final_text.next_to(chain_rule_formula, UP, buff=1.5)
        self.play(Write(final_text))
        
        self.wait(3)
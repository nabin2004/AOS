from manim import *

class ElasticCollision(Scene):
    def construct(self):
        # Constants
        M = 1.0  # Mass of block A (kg)
        m = 0.01  # Mass of block B (kg)
        v0 = 10.0  # Initial velocity of block B (m/s)
        x_a = 10.0  # Initial position of block A (m)
        x_b = 0.0  # Initial position of block B (m)

        # Blocks
        block_a = Rectangle(width=2, height=1, color=BLUE, stroke_width=2, weight=0.6, critical=True)
        block_a.move_to(RIGHT * x_a)
        block_b = Rectangle(width=1, height=0.5, color=RED, stroke_width=2, weight=0.6, critical=True)
        block_b.move_to(LEFT * x_b)
        mass_a_text = Tex(f"M = {M} kg", color=BLUE).next_to(block_a, UP)
        mass_b_text = Tex(f"m = {m} kg", color=RED).next_to(block_b, UP)

        # Velocity vectors
        v_a_arrow = Arrow(color=RED)
        v_b_arrow = Arrow(color=RED)
        v_a_label = DecimalNumber(0, color=RED)
        v_b_label = DecimalNumber(v0, color=RED)

        v_a_arrow.move_to(block_a.get_top() + UP * 0.5)
        v_b_arrow.move_to(block_b.get_top() + UP * 0.5)
        v_a_label.next_to(v_a_arrow, RIGHT)
        v_b_label.next_to(v_b_arrow, RIGHT)

        # Collision counter
        collision_count = 0
        collision_counter_text = Tex(f"# Collisions = {collision_count}").to_edge(UP)

        def update_collision_counter(mob, dt):
            nonlocal collision_count
            collision_counter_text.become(Tex(f"# Collisions = {collision_count}"))

        collision_counter_text.add_updater(update_collision_counter)

        # Conservation equations
        ke_equation = MathTex(r"\frac{1}{2}m_1v_1^2 + \frac{1}{2}m_2v_2^2 = E", color=WHITE)
        momentum_equation = MathTex(r"m_1v_1 + m_2v_2 = P", color=WHITE)
        ke_equation.to_edge(DOWN)
        momentum_equation.next_to(ke_equation, DOWN)
        m1_term = ke_equation[0][0:2]
        v1_term = ke_equation[0][3:6]
        m2_term = ke_equation[0][7:9]
        v2_term = ke_equation[0][10:13]
        m1_term.set_color(BLUE)
        v1_term.set_color(RED)
        m2_term.set_color(BLUE)
        v2_term.set_color(RED)

        m1_term_momentum = momentum_equation[0][0:2]
        v1_term_momentum = momentum_equation[0][3:6]
        m2_term_momentum = momentum_equation[0][7:9]
        v2_term_momentum = momentum_equation[0][10:13]
        m1_term_momentum.set_color(BLUE)
        v1_term_momentum.set_color(RED)
        m2_term_momentum.set_color(BLUE)
        v2_term_momentum.set_color(RED)

        # Phase-space coordinate plane
        axes = Axes(
            x_range=[-5, 5],
            y_range=[-5, 5],
            x_length=4,
            y_length=4,
            axis_config={"include_numbers": False},
        ).to_edge(RIGHT)
        axes.add_coordinate_labels()
        x_label = axes.get_x_axis_label("v₁ (√m₁)")
        y_label = axes.get_y_axis_label("v₂ (√m₂)")
        x_label.shift(RIGHT * 0.5)
        y_label.shift(UP * 0.5)

        # Initial state
        self.play(Create(block_a), Create(block_b), Create(mass_a_text), Create(mass_b_text))
        self.play(Create(v_a_arrow), Create(v_b_arrow), Create(v_a_label), Create(v_b_label))
        self.play(Create(collision_counter_text))
        self.play(Create(ke_equation), Create(momentum_equation))
        self.wait(2)

        # Collision loop
        v_a = 0.0
        v_b = v0
        for i in range(31):
            # Calculate new velocities
            v_a_new = ((M - m) / (M + m)) * v_b + ((2 * m) / (M + m)) * v_a
            v_b_new = ((2 * M) / (M + m)) * v_a - ((M - m) / (M + m)) * v_b

            # Update velocity vectors
            v_a_arrow.set_stroke(color=RED, width=2)
            v_b_arrow.set_stroke(color=RED, width=2)
            v_a_arrow.scale(v_a_new / v0)
            v_b_arrow.scale(v_b_new / v0)
            v_a_label.set_value(v_a_new)
            v_b_label.set_value(v_b_new)

            # Collision animation
            collision_point = block_b.get_center()
            circle = Circle(radius=0.5, color=YELLOW, stroke_width=2).move_to(collision_point)
            self.play(Create(circle), run_time=0.2)
            self.wait(0.1)
            self.play(FadeOut(circle))

            # Update blocks' positions
            block_a.move_to(block_a.get_center() + RIGHT * v_a_new * 0.1)
            block_b.move_to(block_b.get_center() + RIGHT * v_b_new * 0.1)

            # Update collision counter
            collision_count += 1
            collision_counter_text.become(Tex(f"# Collisions = {collision_count}"))

            # Update velocities
            v_a = v_a_new
            v_b = v_b_new

            # Phase-space point
            point = Dot(axes.coords_to_point(np.sqrt(M) * v_a, np.sqrt(m) * v_b), color=RED)
            self.play(Create(point))

        # Final state
        self.play(FadeOut(v_a_arrow, v_b_arrow, v_a_label, v_b_label))
        self.wait(2)
        self.play(Tex("Final State").to_edge(UP))
        self.wait(2)
        self.play(FadeOut(block_a, block_b, mass_a_text, mass_b_text, collision_counter_text, ke_equation, momentum_equation, axes))
        self.wait(1)
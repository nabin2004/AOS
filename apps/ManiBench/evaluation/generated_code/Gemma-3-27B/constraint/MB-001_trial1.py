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
        block_a.set_z_index(1)
        block_b = Rectangle(width=1, height=0.5, color=RED, stroke_width=2, weight=0.6, critical=True)
        block_b.move_to(LEFT * x_b)
        block_b.set_z_index(1)

        # Mass labels
        mass_a_label = Tex(f"M = {M} kg", color=BLUE).next_to(block_a, UP)
        mass_b_label = Tex(f"m = {m} kg", color=RED).next_to(block_b, UP)

        # Velocity vectors
        v_a_arrow = Arrow(color=RED, buff=0.1)
        v_b_arrow = Arrow(color=RED, buff=0.1)
        v_a_label = DecimalNumber(0, color=RED)
        v_b_label = DecimalNumber(v0, color=RED)

        v_a_arrow.add(v_a_label)
        v_b_arrow.add(v_b_label)

        # Collision counter
        collision_count = 0
        collision_counter_text = Tex(f"# Collisions = {collision_count}", color=YELLOW)
        collision_counter_text.to_edge(UP)

        def update_collision_counter(mob, dt):
            global collision_count
            collision_counter_text.become(Tex(f"# Collisions = {collision_count}", color=YELLOW))

        collision_counter_text.add_updater(update_collision_counter)

        # Conservation equations
        ke_equation = MathTex(r"\frac{1}{2}mv_1^2 + \frac{1}{2}mv_2^2 = E", color=WHITE)
        momentum_equation = MathTex(r"m_1v_1 + m_2v_2 = P", color=WHITE)
        ke_equation.to_edge(DOWN)
        momentum_equation.next_to(ke_equation, DOWN)

        # Floor and wall
        floor = Rectangle(width=20, height=0.2, color=GREEN, stroke_width=0.5)
        floor.move_to(DOWN * 0.1)
        wall = Rectangle(width=0.2, height=3, color=GREEN, stroke_width=0.5)
        wall.move_to(RIGHT * 10.2)

        # Initial state
        self.play(Create(floor), Create(wall), Create(block_a), Create(block_b), Write(mass_a_label), Write(mass_b_label))
        self.play(Create(v_a_arrow.copy().move_to(block_a.get_top() + UP * 0.5)), Create(v_b_arrow.copy().move_to(block_b.get_top() + UP * 0.5)))
        self.wait(1)

        # Collision loop
        def collision_event():
            global collision_count, v0
            collision_count += 1
            # Calculate velocities after collision (elastic collision formulas)
            v_a = (2 * m * v0) / (M + m)
            v_b = ((M - m) * v0) / (M + m)

            # Update velocity vectors
            v_a_arrow.set_angle(atan2(0, 1) if v_a > 0 else atan2(0, -1))
            v_a_arrow.set_length(abs(v_a))
            v_a_label.set_value(v_a)
            v_b_arrow.set_angle(atan2(0, 1) if v_b > 0 else atan2(0, -1))
            v_b_arrow.set_length(abs(v_b))
            v_b_label.set_value(v_b)

            # Move blocks
            block_a.move_to(block_a.get_center() + RIGHT * v_a)
            block_b.move_to(block_b.get_center() + RIGHT * v_b)

            # Collision feedback
            circle = Circle(radius=0.5, color=YELLOW, opacity=0.5)
            circle.move_to(block_a.get_center())
            self.play(Create(circle), run_time=0.2)
            self.play(FadeOut(circle), run_time=0.1)

            # Update conservation equations
            ke_equation[0][0].set_value(m)
            ke_equation[0][3].set_value(v_a)
            ke_equation[0][6].set_value(m)
            ke_equation[0][9].set_value(v_b)
            momentum_equation[0][0].set_value(M)
            momentum_equation[0][3].set_value(v_a)
            momentum_equation[0][6].set_value(m)
            momentum_equation[0][9].set_value(v_b)

        # Simulate collisions
        for _ in range(31):
            self.play(MoveAlongPath(block_b, Line(block_b.get_center(), block_a.get_center())), MoveAlongPath(block_a, Line(block_a.get_center(), block_b.get_center())),
                      UpdateFromFunc(v_a_arrow, lambda mob: mob.set_angle(atan2(0, 1) if v_a > 0 else atan2(0, -1)).set_length(abs(v_a))),
                      UpdateFromFunc(v_a_label, lambda mob: mob.set_value(v_a)),
                      UpdateFromFunc(v_b_arrow, lambda mob: mob.set_angle(atan2(0, 1) if v_b > 0 else atan2(0, -1)).set_length(abs(v_b))),
                      UpdateFromFunc(v_b_label, lambda mob: mob.set_value(v_b)),
                      collision_event)
            self.wait(0.1)

        # Final state
        self.play(FadeOut(v_a_arrow), FadeOut(v_b_arrow), FadeOut(v_a_label), FadeOut(v_b_label))
        self.wait(1)

        # Phase-space diagram
        axes = Axes(x_range=[-5, 5], y_range=[-5, 5], x_length=5, y_length=5, axis_config={"include_numbers": True})
        axes.add_coordinate_labels()
        axes.set_axis_orientations(DOWN, RIGHT)
        axes.shift(DOWN * 2)

        # Energy circle
        E = 12.5  # Total energy
        circle = Circle(radius=sqrt(E), color=BLUE)
        circle.move_to(axes.c2p(0, 0))

        # Momentum line
        slope = -sqrt(m / M)
        line = Line(axes.c2p(-5, 5 * slope), axes.c2p(5, -5 * slope), color=GREEN)

        # State point
        state_point = Dot(axes.c2p(sqrt(m) * v0, 0), color=RED)

        # Display equations
        equation_circle = MathTex(r"x^2 + y^2 = 2E", color=WHITE).next_to(axes, UP)

        self.play(Create(axes), Create(circle), Create(line), Create(state_point), Write(equation_circle))
        self.wait(2)

        # Final message
        final_text = Tex("Collision count approximates digits of π", color=YELLOW).to_edge(UP)
        self.play(Write(final_text))
        self.wait(3)
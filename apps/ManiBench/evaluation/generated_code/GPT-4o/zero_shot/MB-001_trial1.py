from manim import *

class ElasticCollisionAnimation(Scene):
    def elastic_collision(self, v1, v2, m1, m2):
        # Elastic collision velocity update formulas
        new_v1 = (v1 * (m1 - m2) + 2 * m2 * v2) / (m1 + m2)
        new_v2 = (v2 * (m2 - m1) + 2 * m1 * v1) / (m1 + m2)
        return new_v1, new_v2

    def construct(self):
        # Constants
        m1 = 1  # Mass of Block A
        m2 = 100  # Mass of Block B
        v1 = 0  # Initial velocity of Block A
        v2 = 5  # Initial velocity of Block B
        collision_count = 0

        # Blocks
        block_a = Square(side_length=1, color=BLUE).shift(RIGHT * 4)
        block_b = Square(side_length=1, color=RED).shift(LEFT * 4)

        # Velocity vectors
        v1_arrow = Arrow(block_a.get_top(), block_a.get_top() + UP * v1, buff=0, color=BLUE)
        v2_arrow = Arrow(block_b.get_top(), block_b.get_top() + UP * v2, buff=0, color=RED)

        # Collision counter
        counter_text = Text(f"Collisions: {collision_count}", font_size=24).to_corner(UP + LEFT)

        # Energy and momentum equations
        energy_eq = MathTex(r"\frac{1}{2}m_1v_1^2 + \frac{1}{2}m_2v_2^2 = E").to_corner(UP + RIGHT)
        momentum_eq = MathTex(r"m_1v_1 + m_2v_2 = P").next_to(energy_eq, DOWN)

        # Add initial elements
        self.add(block_a, block_b, v1_arrow, v2_arrow, counter_text, energy_eq, momentum_eq)

        # Animation loop for collisions
        while v2 > v1:
            # Move blocks until collision
            time_to_collision = (block_a.get_x() - block_b.get_x() - 1) / (v2 - v1)
            self.play(
                block_a.animate.shift(RIGHT * v1 * time_to_collision),
                block_b.animate.shift(RIGHT * v2 * time_to_collision),
                v1_arrow.animate.shift(RIGHT * v1 * time_to_collision),
                v2_arrow.animate.shift(RIGHT * v2 * time_to_collision),
                run_time=time_to_collision,
                rate_func=linear
            )

            # Update velocities after collision
            v1, v2 = self.elastic_collision(v1, v2, m1, m2)
            collision_count += 1

            # Update velocity vectors and counter
            new_v1_arrow = Arrow(block_a.get_top(), block_a.get_top() + UP * v1, buff=0, color=BLUE)
            new_v2_arrow = Arrow(block_b.get_top(), block_b.get_top() + UP * v2, buff=0, color=RED)
            new_counter_text = Text(f"Collisions: {collision_count}", font_size=24).to_corner(UP + LEFT)

            self.play(
                Transform(v1_arrow, new_v1_arrow),
                Transform(v2_arrow, new_v2_arrow),
                Transform(counter_text, new_counter_text)
            )

        # Final state
        final_text = Text(f"# Collisions = {collision_count}", font_size=36).to_edge(DOWN)
        self.play(Write(final_text))

        # Phase-space visualization
        phase_space = Axes(
            x_range=[-10, 10, 2],
            y_range=[-10, 10, 2],
            axis_config={"include_numbers": True}
        ).to_corner(DOWN + LEFT)
        phase_space_labels = phase_space.get_axis_labels(
            Tex(r"\sqrt{m_1}v_1"), Tex(r"\sqrt{m_2}v_2")
        )
        self.play(Create(phase_space), Write(phase_space_labels))

        # Trace phase-space trajectory
        trajectory = VMobject(color=YELLOW)
        trajectory.set_points_as_corners([phase_space.coords_to_point(0, 0)])
        self.add(trajectory)

        v1_scaled = v1 * (m1**0.5)
        v2_scaled = v2 * (m2**0.5)
        while v2 > v1:
            # Update phase-space point
            new_point = phase_space.coords_to_point(v1_scaled, v2_scaled)
            trajectory.add_points_as_corners([new_point])

            # Update velocities
            v1, v2 = self.elastic_collision(v1, v2, m1, m2)
            v1_scaled = v1 * (m1**0.5)
            v2_scaled = v2 * (m2**0.5)

        # Show momentum conservation line and energy circle
        energy_circle = Circle(radius=(m1 * v1**2 + m2 * v2**2)**0.5, color=GREEN).move_to(phase_space.coords_to_point(0, 0))
        momentum_line = Line(
            phase_space.coords_to_point(-10, 10 * (m1 / m2)**0.5),
            phase_space.coords_to_point(10, -10 * (m1 / m2)**0.5),
            color=RED
        )
        self.play(Create(energy_circle), Create(momentum_line))

        # Slow-motion replay for high mass ratios
        self.wait(2)
        self.play(FadeOut(trajectory, energy_circle, momentum_line, final_text))
        self.wait()
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
            # Elastic collision formulas
            v1 = (M * v0) / (M + m)
            v2 = (M * v0 - m * v0) / (M + m)
            
            # Update velocities
            v_a_label.set_value(v1)
            v_b_label.set_value(v2)
            
            # Update velocity vectors
            v_a_arrow.set_angle(np.arctan(v1/1))
            v_b_arrow.set_angle(np.arctan(v2/1))
            
            # Collision feedback
            circle = Circle(radius=0.5, color=YELLOW, opacity=0.5)
            circle.move_to(block_a.get_center())
            self.play(Create(circle), run_time=0.2)
            self.play(FadeOut(circle), run_time=0.2)
            
            # Update block positions
            block_a.move_to(block_a.get_center() + RIGHT * v1)
            block_b.move_to(block_b.get_center() + RIGHT * v2)

        # Simulate collisions
        for _ in range(31):
            if block_b.get_center()[0] < block_a.get_center()[0]:
                collision_event()
            else:
                break
            self.wait(0.1)

        # Final state
        self.wait(1)
        self.play(FadeOut(v_a_arrow, v_b_arrow, v_a_label, v_b_label))
        self.play(Write(ke_equation), Write(momentum_equation))
        self.wait(2)

        # Phase-space diagram
        axes = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=6, y_length=6)
        axes.add_coordinate_labels()
        axes.shift(DOWN * 2)
        
        # Energy circle
        E = (0.5 * m * v0**2)
        circle = Circle(radius=np.sqrt(2 * E / m), color=BLUE)
        circle.move_to(ORIGIN)
        
        # Momentum line
        slope = -np.sqrt(M / m)
        line = Line(start=axes.c2p((-5, 0)), end=axes.c2p((5, -5 * slope)), color=GREEN)
        
        # State point
        state_point = Dot(axes.c2p((np.sqrt(m * v0**2), 0)), color=RED)
        
        self.play(Create(axes), Create(circle), Create(line), Create(state_point))
        self.wait(2)

        # Slow-motion replay for high mass ratios
        self.play(
            RunTime(10),
            self.play(
                *[(Create(block_a.copy()), Create(block_b.copy())) for _ in range(10)],
                *[(Create(v_a_arrow.copy().move_to(block_a.get_top() + UP * 0.5)), Create(v_b_arrow.copy().move_to(block_b.get_top() + UP * 0.5))) for _ in range(10)]
            )
        )
        self.wait(1)
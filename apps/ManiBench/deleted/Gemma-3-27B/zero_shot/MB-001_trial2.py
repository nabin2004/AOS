from manim import *

class ElasticCollision(Scene):
    def construct(self):
        # Parameters
        M = 1  # Mass of block A
        m = 0.01  # Mass of block B
        v0 = 5  # Initial velocity of block B
        x_A = 10
        x_B = 0
        n = 0
        E = 0.5 * m * v0**2
        P = m * v0

        # Blocks
        block_A = Rectangle(width=1, height=1, color=BLUE, label="M")
        block_A.move_to(RIGHT * x_A)
        block_B = Rectangle(width=1, height=1, color=RED, label="m")
        block_B.move_to(LEFT * 0 + RIGHT * x_B)

        # Velocity vectors
        v_A_arrow = Arrow(color=BLUE, buff=0.2)
        v_B_arrow = Arrow(color=RED, buff=0.2)

        # Collision counter
        collision_count_text = Text("Collisions = 0", font_size=24)
        collision_count_text.to_edge(UP)

        # Conservation equations
        ke_eq = MathTex(r"\frac{1}{2}m_1v_1^2 + \frac{1}{2}m_2v_2^2 = E", font_size=24)
        ke_eq.next_to(collision_count_text, DOWN)
        momentum_eq = MathTex(r"m_1v_1 + m_2v_2 = P", font_size=24)
        momentum_eq.next_to(ke_eq, DOWN)

        # Phase space
        ax = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=4,
            y_length=4,
            axis_config={"include_numbers": False},
        )
        ax.add_coordinate_labels()
        ax.shift(DOWN * 3)

        # Ellipse/Circle
        ellipse = ax.plot(lambda x: np.sqrt(E - m * x**2) / np.sqrt(m), x_range=[0, np.sqrt(E / m)])
        
        # Momentum line
        slope = -np.sqrt(M / m)
        intercept = P / np.sqrt(m)
        momentum_line = ax.plot(lambda x: slope * x + intercept, x_range=[0, np.sqrt(E / m)])

        # Initial state
        self.play(Create(block_A), Create(block_B))
        v_A_arrow.put_start_at(block_A).set_end_at(block_A + RIGHT * v0 * 0.5)
        v_B_arrow.put_start_at(block_B).set_end_at(block_B + RIGHT * v0 * 0.5)
        self.play(Create(v_A_arrow), Create(v_B_arrow))
        self.play(Create(collision_count_text), Create(ke_eq), Create(momentum_eq))
        self.play(Create(ax), Create(ellipse), Create(momentum_line))

        # Collision loop
        while n < 31:
            # Calculate velocities after collision
            v_A = (2 * v0 * m) / (M + m)
            v_B = (v0 * (M - m)) / (M + m)

            # Update blocks
            block_A.generate_target()
            block_B.generate_target()
            block_A.target.move_to(block_A.get_center() + RIGHT * v_A * 0.5)
            block_B.target.move_to(block_B.get_center() + RIGHT * v_B * 0.5)

            # Update velocity vectors
            v_A_arrow.generate_target()
            v_B_arrow.generate_target()
            v_A_arrow.target.put_start_at(block_A.target).set_end_at(block_A.target + RIGHT * v_A * 0.5)
            v_B_arrow.target.put_start_at(block_B.target).set_end_at(block_B.target + RIGHT * v_B * 0.5)

            # Increment collision counter
            n += 1
            collision_count_text.become(Text(f"Collisions = {n}", font_size=24))

            # Animate collision
            self.play(
                MoveToTarget(block_A),
                MoveToTarget(block_B),
                MoveToTarget(v_A_arrow),
                MoveToTarget(v_B_arrow),
                collision_count_text.animate.become(Text(f"Collisions = {n}", font_size=24))
            )

            # Update velocities for next iteration
            v0 = v_B
            
            if v0 <= 0.1:
                break

        # Final state
        self.play(Wait(1))
        self.play(FadeOut(v_A_arrow, v_B_arrow, collision_count_text, ke_eq, momentum_eq, ax, ellipse, momentum_line))
        self.play(block_A.animate.move_to(RIGHT * 20), block_B.animate.move_to(LEFT * 5))
        self.wait(2)
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
        ke_eq = Tex(r"$\frac{1}{2}mv_1^2 + \frac{1}{2}Mv_2^2 = E$", font_size=24)
        ke_eq.next_to(collision_count_text, DOWN)
        momentum_eq = Tex(r"$mv_1 + Mv_2 = P$", font_size=24)
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
        ellipse = ax.plot(lambda x: np.sqrt(E - 0.5 * M * x**2), color=GREEN)

        # Momentum line
        slope = -np.sqrt(M / m)
        intercept = P / m
        momentum_line = ax.plot(lambda x: slope * x + intercept, color=YELLOW)

        # Initial state
        self.play(Create(block_A), Create(block_B))
        v_A_arrow.put_start_at(block_A).set_end_at(block_A + RIGHT * v0 * 0.5)
        v_B_arrow.put_start_at(block_B).set_end_at(block_B + RIGHT * v0 * 0.5)
        self.play(Create(v_A_arrow), Create(v_B_arrow))
        self.play(Write(collision_count_text), Write(ke_eq), Write(momentum_eq))
        self.play(Create(ax), Create(ellipse), Create(momentum_line))

        # Collision loop
        while n < 31:
            # Calculate velocities after collision
            v1 = (P - M * 0) / m
            v2 = (M * v0 - m * 0) / M

            # Update blocks
            block_A.move_to(block_A + RIGHT * v2 * 0.1)
            block_B.move_to(block_B + RIGHT * v1 * 0.1)

            # Update velocity vectors
            v_A_arrow.set_end_at(block_A + RIGHT * v2 * 0.5)
            v_B_arrow.set_end_at(block_B + RIGHT * v1 * 0.5)

            # Increment collision counter
            n += 1
            collision_count_text.become_transform(
                Text(f"Collisions = {n}", font_size=24)
            )

            self.play(
                MoveAlongPath(v_A_arrow, block_A),
                MoveAlongPath(v_B_arrow, block_B),
                UpdateFromFunc(block_A, lambda x: x),
                UpdateFromFunc(block_B, lambda x: x),
                Write(collision_count_text)
            )

            # Check for end condition (v1 <= v2)
            if v1 <= v2:
                break

        # Final state
        self.play(
            block_A.animate.move_to(block_A + RIGHT * 5),
            block_B.animate.move_to(block_B + RIGHT * 0)
        )
        self.play(FadeOut(v_A_arrow, v_B_arrow))
        self.wait(2)
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
        ax.add(Tex(r"$\sqrt{mv_1}$", ax.get_x_axis().label))
        ax.add(Tex(r"$\sqrt{Mv_2}$", ax.get_y_axis().label))

        # Initial state
        self.play(Create(block_A), Create(block_B))
        self.play(Create(v_B_arrow.copy().move_to(block_B).set_angle(0)))
        self.play(Write(collision_count_text), Write(ke_eq), Write(momentum_eq))

        # Simulation loop
        for i in range(31):
            # Calculate velocities after collision
            v_A = (2 * v0 * m) / (M + m)
            v_B = v0 - v_A

            # Update block positions
            block_A.move_to(block_A.get_center() + RIGHT * v_A)
            block_B.move_to(block_B.get_center() + RIGHT * v_B)

            # Update velocity vectors
            v_A_arrow.move_to(block_A).set_angle(0)
            v_B_arrow.move_to(block_B).set_angle(0)

            # Increment collision counter
            n += 1
            collision_count_text.set_text(f"Collisions = {n}")

            # Phase space point
            point = Dot(ax.c2p(np.sqrt(m * v_A), np.sqrt(M * v_B)), color=GREEN)
            ax.add(point)

            self.play(
                Transform(v_A_arrow, v_A_arrow.copy().move_to(block_A).set_angle(0)),
                Transform(v_B_arrow, v_B_arrow.copy().move_to(block_B).set_angle(0)),
                Update(collision_count_text),
                Create(point),
                run_time=0.1
            )

            # Check for end condition (v_B <= 0)
            if v_B <= 0:
                break

        # Final state
        self.play(
            block_B.animate.move_to(LEFT * 5),
            v_B_arrow.animate.set_angle(180),
            run_time=1
        )

        # Mass ratio demonstration
        self.play(FadeOut(block_A, block_B, v_A_arrow, v_B_arrow, collision_count_text, ke_eq, momentum_eq))

        # Phase space ellipse
        ellipse = ax.plot(lambda x: np.sqrt(E - m * x**2) / np.sqrt(M), x_range=[0, np.sqrt(E / m)], color=YELLOW)
        ax.add(ellipse)

        # Momentum conservation line
        line = ax.plot(lambda x: (P - m * x) / M, x_range=[0, P / m], color=ORANGE)
        ax.add(line)

        self.play(Create(ax), Create(ellipse), Create(line))

        # Arc angle argument
        theta = np.arctan(np.sqrt(m / M))
        angle_text = Tex(r"$\theta = \arctan(\sqrt{\frac{m}{M}})$", font_size=24).to_edge(DOWN)
        self.play(Write(angle_text))

        self.wait(2)
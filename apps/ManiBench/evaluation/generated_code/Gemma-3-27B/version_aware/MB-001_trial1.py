from manim import *

class ElasticCollision(Scene):
    def construct(self):
        M = 1
        m = 0.01
        v0 = 5
        n = 0
        dt = 0.02

        block_A = Rectangle(width=0.5, height=0.5, color=RED)
        block_A.move_to(RIGHT * 10)
        block_B = Rectangle(width=0.5, height=0.5, color=BLUE)
        block_B.move_to(LEFT * 0)

        arrow_A = Arrow(block_A.get_center(), block_A.get_center() + RIGHT * 0, buff=0)
        arrow_B = Arrow(block_B.get_center(), block_B.get_center() + RIGHT * v0, buff=0)

        collision_count = Text("Collisions = 0")
        collision_count.to_corner(UP)

        ke_text = Tex(r"½m₁v₁² + ½m₂v₂² = E")
        ke_text.next_to(collision_count, DOWN)
        momentum_text = Tex(r"m₁v₁ + m₂v₂ = P")
        momentum_text.next_to(ke_text, DOWN)

        self.play(Create(block_A), Create(block_B), Create(arrow_A), Create(arrow_B))
        self.wait(1)

        vx_A = 0
        vx_B = v0

        while n < 31:
            if block_B.get_center()[0] > block_A.get_center()[0] and vx_B > 0:
                # Collision
                v1 = (M * vx_A + m * vx_B) / (M + m)
                v2 = (m * vx_A + M * vx_B) / (M + m)
                vx_A = v1
                vx_B = v2

                n += 1
                collision_count.become(Text(f"Collisions = {n}"))

                self.play(
                    Transform(arrow_A, Arrow(block_A.get_center(), block_A.get_center() + RIGHT * vx_A, buff=0)),
                    Transform(arrow_B, Arrow(block_B.get_center(), block_B.get_center() + RIGHT * vx_B, buff=0)),
                    Transform(collision_count, Text(f"Collisions = {n}"))
                )
                self.wait(dt)

            block_A.shift(RIGHT * vx_A * dt)
            block_B.shift(RIGHT * vx_B * dt)
            arrow_A.shift(RIGHT * vx_A * dt)
            arrow_B.shift(RIGHT * vx_B * dt)

        self.wait(2)

        # Phase space
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=5,
            y_length=5,
            axis_config={"include_numbers": False}
        )
        axes.add_coordinate_labels()
        axes.shift(DOWN * 2)

        circle = Circle(radius=2, color=GREEN)
        circle.move_to(ORIGIN)

        line = Line(start=LEFT * 5, end=RIGHT * 5, color=YELLOW)
        line.move_to(DOWN * 1)

        self.play(Create(axes), Create(circle), Create(line))
        self.wait(2)

        # Demonstrate different mass ratios
        for ratio in [1, 16, 100, 10000, 1000000]:
            M = ratio
            m = 1
            v0 = 5
            n = 0
            vx_A = 0
            vx_B = v0
            block_A = Rectangle(width=0.5, height=0.5, color=RED)
            block_A.move_to(RIGHT * 10)
            block_B = Rectangle(width=0.5, height=0.5, color=BLUE)
            block_B.move_to(LEFT * 0)
            arrow_A = Arrow(block_A.get_center(), block_A.get_center() + RIGHT * 0, buff=0)
            arrow_B = Arrow(block_B.get_center(), block_B.get_center() + RIGHT * v0, buff=0)
            collision_count = Text(f"Collisions = {n}")
            collision_count.to_corner(UP)

            self.play(
                Transform(block_A, Rectangle(width=0.5, height=0.5, color=RED)),
                Transform(block_B, Rectangle(width=0.5, height=0.5, color=BLUE)),
                Transform(arrow_A, Arrow(block_A.get_center(), block_A.get_center() + RIGHT * 0, buff=0)),
                Transform(arrow_B, Arrow(block_B.get_center(), block_B.get_center() + RIGHT * v0, buff=0)),
                Transform(collision_count, Text(f"Collisions = {n}"))
            )

            while n < 31:
                if block_B.get_center()[0] > block_A.get_center()[0] and vx_B > 0:
                    # Collision
                    v1 = (M * vx_A + m * vx_B) / (M + m)
                    v2 = (m * vx_A + M * vx_B) / (M + m)
                    vx_A = v1
                    vx_B = v2

                    n += 1
                    collision_count.become(Text(f"Collisions = {n}"))

                    self.play(
                        Transform(arrow_A, Arrow(block_A.get_center(), block_A.get_center() + RIGHT * vx_A, buff=0)),
                        Transform(arrow_B, Arrow(block_B.get_center(), block_B.get_center() + RIGHT * vx_B, buff=0)),
                        Transform(collision_count, Text(f"Collisions = {n}"))
                    )
                    self.wait(dt)

                block_A.shift(RIGHT * vx_A * dt)
                block_B.shift(RIGHT * vx_B * dt)
                arrow_A.shift(RIGHT * vx_A * dt)
                arrow_B.shift(RIGHT * vx_B * dt)

            self.wait(1)
from manim import *

# Analysis:
# 1. Mobjects: Blocks (3D), Velocity Vectors (Arrows), Collision Counter (Text),
#    Conservation Equations (Tex), Phase-Space Plane (NumberPlane), State Point (Dot),
#    Momentum Line (Line), End Zone (Polygon), Labels (Text).
# 2. Order: Initial setup, collision animation, conservation laws, phase space,
#    mass ratio demonstration, slow-motion replay, conclusion.
# 3. Transformations: Translation, scaling, rotation, fading, updating.
# 4. Synchronization: Use `add`, `animate`, `wait`, and `updater` for timing.
# 5. Labels/Formulas: Mass labels, velocity values, KE/momentum equations,
#    phase-space equations, collision count, mass ratios.

class ElasticCollision(Scene):
    def construct(self):
        # Constants
        M = 1.0
        m = 0.01
        v0 = 5.0
        x_a = 10.0
        x_b = 0.0

        # Blocks
        block_a = ThreeDBlock(color=BLUE, mass=M, position=[x_a, 0, 0])
        block_b = ThreeDBlock(color=RED, mass=m, position=[x_b, 0, 0])

        # Velocity vectors
        arrow_a = Arrow(color=BLUE, start=[x_a, 0, 0], end=[x_a, 0, 1], buff=0)
        arrow_b = Arrow(color=RED, start=[x_b, 0, 0], end=[x_b, 0, 1], buff=0)
        arrow_a.scale(v0)
        arrow_b.scale(v0)

        # Collision counter
        collision_count = 0
        collision_counter_text = Text(f"# Collisions = {collision_count}", font_size=24)
        collision_counter_text.to_corner(UR)

        # Conservation equations
        ke_equation = Tex(r"½m₁v₁² + ½m₂v₂² = E", font_size=24)
        momentum_equation = Tex(r"m₁v₁ + m₂v₂ = P", font_size=24)
        ke_equation.next_to(momentum_equation, UP)
        momentum_equation.to_corner(UL)

        # Phase-space plane
        phase_space = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=6, y_length=6)
        phase_space.add_coordinate_labels()
        phase_space.to_edge(DOWN)

        # State point
        state_point = Dot(color=RED)
        state_point.move_to(phase_space.c2p(v0, 0))

        # Momentum line
        slope = -np.sqrt(M / m)
        momentum_line = Line(phase_space.c2p(-5, slope * -5), phase_space.c2p(5, slope * 5), color=GREEN)

        # End zone
        end_zone = Polygon([phase_space.c2p(0, 0), phase_space.c2p(5, 0), phase_space.c2p(5, 5), phase_space.c2p(0, 5)], color=GREEN, opacity=0.5)

        # Add initial objects
        self.add(block_a, block_b, arrow_a, arrow_b, collision_counter_text, ke_equation, momentum_equation, phase_space, state_point, momentum_line, end_zone)

        # Animation loop
        def update_scene(mob, dt):
            nonlocal collision_count
            nonlocal block_a, block_b, arrow_a, arrow_b, state_point

            # Block B moves
            block_b.shift(RIGHT * v0 * dt)
            arrow_b.shift(RIGHT * v0 * dt)

            # Collision detection
            if block_b.get_center()[0] >= block_a.get_center()[0]:
                # Collision occurs
                collision_count += 1
                collision_counter_text.become(Text(f"# Collisions = {collision_count}", font_size=24).to_corner(UR))

                # Calculate new velocities (elastic collision)
                v1 = (M * v0 - m * v0) / (M + m)
                v2 = (2 * M * v0) / (M + m)

                # Update velocities
                arrow_a.set_length(v1)
                arrow_b.set_length(v2)
                arrow_a.move_to([block_a.get_center()[0], 0, 0])
                arrow_b.move_to([block_b.get_center()[0], 0, 0])

                # Update state point
                state_point.move_to(phase_space.c2p(v1, v2))

                # Visual feedback
                circle = Circle(radius=0.5, color=YELLOW, stroke_width=2)
                circle.move_to(block_a.get_center())
                self.play(Create(circle), run_time=0.1)
                self.play(FadeOut(circle), run_time=0.1)

                # Update block positions
                block_a.shift(RIGHT * v1 * dt)
                block_b.shift(RIGHT * v2 * dt)

            else:
                # Block A remains stationary
                block_a.shift(RIGHT * 0 * dt)

        self.add_updater(update_scene)
        self.wait(10)

        # Demonstrate mass ratios
        self.clear()
        self.add(Text("Demonstrating Mass Ratios", font_size=36).to_edge(UP))

        for ratio in [1, 16, 100, 10000, 1000000, 100000000, 10000000000]:
            M = ratio
            m = 1
            v0 = 5.0
            x_a = 10.0
            x_b = 0.0

            block_a = ThreeDBlock(color=BLUE, mass=M, position=[x_a, 0, 0])
            block_b = ThreeDBlock(color=RED, mass=m, position=[x_b, 0, 0])
            arrow_a = Arrow(color=BLUE, start=[x_a, 0, 0], end=[x_a, 0, 1], buff=0)
            arrow_b = Arrow(color=RED, start=[x_b, 0, 0], end=[x_b, 0, 1], buff=0)
            arrow_a.scale(v0)
            arrow_b.scale(v0)

            self.play(Create(block_a), Create(block_b), Create(arrow_a), Create(arrow_b))
            self.wait(2)
            self.clear()

        self.add(Text("Collision Count and π", font_size=36).to_edge(UP))
        self.add(Text("Collision count approximates digits of π", font_size=24))
        self.wait(2)

class ThreeDBlock(VGroup):
    def __init__(self, color, mass, position):
        super().__init__()
        block = Box(width=2, height=1, depth=1, color=color)
        mass_label = Text(f"M = {mass}", font_size=12)
        mass_label.next_to(block, UP)
        self.add(block, mass_label)
        self.move_to(position)
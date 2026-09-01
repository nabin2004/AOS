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
        arrow_a = Arrow(color=BLUE, start=[x_a, 0, 0], end=[x_a, 0, 1], tip_length=0.5)
        arrow_b = Arrow(color=RED, start=[x_b, 0, 0], end=[x_b, 0, 1], tip_length=0.5)

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

        # Momentum line
        momentum_line = Line(start=[-5, 0], end=[5, -5 * (M / m)**0.5], color=GREEN)

        # End zone
        end_zone = Polygon([0, 0], [5, 0], [5, -5 * (M / m)**0.5], [0, -5 * (M / m)**0.5], color=GREEN, opacity=0.5)

        # Initial state
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

                # Elastic collision formulas
                v1_after = (M * v0 - m * 0) / (M + m)
                v2_after = (2 * M * v0) / (M + m)

                # Update block A's velocity
                block_a.shift(RIGHT * v1_after * dt)
                arrow_a.become(Arrow(color=BLUE, start=block_a.get_center(), end=[block_a.get_center()[0], block_a.get_center()[1], block_a.get_center()[1] + 1], tip_length=0.5))

                # Update block B's velocity
                block_b.shift(RIGHT * v2_after * dt)
                arrow_b.become(Arrow(color=RED, start=block_b.get_center(), end=[block_b.get_center()[0], block_b.get_center()[1], block_b.get_center()[1] + 1], tip_length=0.5))

                # Update phase-space point
                state_point.move_to([np.sqrt(M * v1_after), np.sqrt(m * v2_after)])

                # Add collision effect
                circle = Circle(radius=0.5, color=YELLOW, stroke_width=2)
                circle.move_to(block_a.get_center())
                self.play(Create(circle), run_time=0.2)
                self.play(FadeOut(circle), run_time=0.1)

                # Check if in end zone
                if v1_after <= v2_after:
                    self.play(StopAnimation(self))
                    self.play(Text("Collision stopped").to_corner(DL))

            # Update phase space
            #state_point.move_to([np.sqrt(M * block_a.velocity[0]), np.sqrt(m * block_b.velocity[0])])

        self.play(Wait(2))
        self.add_updater(update_scene)
        self.wait(10)

class ThreeDBlock(VGroup):
    def __init__(self, color=BLUE, mass=1.0, position=[0, 0, 0], **kwargs):
        super().__init__(**kwargs)
        self.color = color
        self.mass = mass
        self.position = position
        self.block = Box(width=1, height=1, depth=1, color=self.color)
        self.mass_label = Text(f"M = {self.mass}", font_size=12, color=WHITE)
        self.mass_label.next_to(self.block, UP)
        self.add(self.block, self.mass_label)
        self.move_to(self.position)
        self.velocity = [0, 0, 0]
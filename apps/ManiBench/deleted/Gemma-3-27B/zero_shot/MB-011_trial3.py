from manim import *

class HairyBallTheorem(Scene):
    def construct(self):
        # 1. 3D Sphere with Rotation
        sphere = Sphere(radius=2, resolution=(32, 32))
        sphere.set_fill(BLUE_E, opacity=0.5)
        self.play(Create(sphere))
        self.play(Rotate(sphere, angle=TAU, axis=Z, run_time=5))

        # 2. Vector Field (Arrows)
        num_arrows = 100
        arrows = VGroup(*[Arrow(radius=0.1, color=YELLOW) for _ in range(num_arrows)])
        
        def get_arrow_positions(sphere, num_arrows):
            positions = []
            for _ in range(num_arrows):
                angle1 = np.random.uniform(0, TAU)
                angle2 = np.random.uniform(0, PI)
                x = sphere.radius * np.sin(angle2) * np.cos(angle1)
                y = sphere.radius * np.sin(angle2) * np.sin(angle1)
                z = sphere.radius * np.cos(angle2)
                positions.append(np.array([x, y, z]))
            return positions

        arrow_positions = get_arrow_positions(sphere, num_arrows)
        for i, arrow in enumerate(arrows):
            arrow.move_to(arrow_positions[i])
            arrow.set_angle(np.random.uniform(0, TAU))
        
        self.play(Create(arrows))

        # 3. Attempt Continuous Orientation
        self.play(
            *[
                arrow.animate.set_angle(arrow.angle + 0.1)
                for arrow in arrows
            ],
            run_time=5
        )

        # 4. Show Impossibility - Bald Spot
        bald_spot = Dot(radius=0.1, color=RED)
        bald_spot.move_to(UP * sphere.radius)  # Example bald spot location
        self.play(Create(bald_spot))
        self.play(
            Indicate(bald_spot, color=RED, scale_factor=1.2),
            Write(Text("Bald Spot", font_size=24, color=RED).next_to(bald_spot, UP))
        )

        # 5. Combing Process (Simplified)
        # This is a simplification.  A true demonstration would be much more complex.
        line1 = Line(start=LEFT * sphere.radius, end=RIGHT * sphere.radius, color=GREEN)
        line2 = Line(start=DOWN * sphere.radius, end=UP * sphere.radius, color=ORANGE)
        self.play(Create(line1), Create(line2))
        
        self.play(
            line1.animate.shift(UP * 0.5),
            line2.animate.shift(RIGHT * 0.5)
        )
        
        self.play(
            Write(Text("Tangency Requirements Fail", font_size=24, color=WHITE).to_edge(DOWN))
        )

        # 6. Highlight Bald Spot
        self.play(
            Indicate(bald_spot, color=RED, scale_factor=1.5),
            FadeOut(line1, line2)
        )
        
        self.wait(2)
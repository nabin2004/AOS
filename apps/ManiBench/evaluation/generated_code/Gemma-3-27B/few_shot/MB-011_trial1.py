from manim import *

class HairyBallTheorem(ThreeDScene):
    def construct(self):
        sphere = Sphere(radius=2, resolution=(32, 32))
        self.play(Rotate(sphere, axis=Z_AXIS, angle=TAU, run_time=5))

        # Vector field
        num_vectors = 64
        vectors = VGroup()
        for i in range(num_vectors):
            phi = i / num_vectors * TAU
            x = sphere.radius * np.sin(phi)
            y = sphere.radius * np.cos(phi)
            z = 0
            vector = Arrow3D(
                start=sphere.point_from_angle(phi),
                end=sphere.point_from_angle(phi) + Vector3(np.sin(phi), -np.cos(phi), 0) * 0.5,
                color=YELLOW,
                buff=0
            )
            vectors.add(vector)
        self.play(Create(vectors))

        # Attempt continuous orientation
        self.play(Rotate(vectors, axis=Z_AXIS, angle=TAU, run_time=5))
        self.wait(1)

        # Show impossibility - combing
        self.play(
            vectors.animate.shift(LEFT * 0.5).scale(0.8),
            run_time=2
        )
        self.wait(1)

        # Highlight bald spot
        bald_spot = sphere.point_from_angle(np.pi)
        bald_spot_marker = Circle(radius=0.2, color=RED, fill_opacity=1)
        bald_spot_marker.move_to(bald_spot)
        bald_spot_text = Text("Bald Spot", font_size=24, color=RED).next_to(bald_spot_marker, UP)

        self.play(Create(bald_spot_marker), Write(bald_spot_text))
        self.wait(2)

        # Combing animation
        comb_lines = VGroup()
        num_lines = 16
        for i in range(num_lines):
            angle = i / num_lines * TAU
            line = Line(
                start=sphere.point_from_angle(angle),
                end=sphere.point_from_angle(angle + PI / num_lines),
                color=GREEN
            )
            comb_lines.add(line)

        self.play(Create(comb_lines))
        self.wait(1)

        # Show tangency failure
        self.play(
            vectors.animate.shift(RIGHT * 0.5).scale(1.2),
            run_time=2
        )
        self.wait(2)

        self.play(FadeOut(vectors, comb_lines))
        self.play(Rotate(sphere, axis=Z_AXIS, angle=TAU, run_time=5))
        self.wait(1)
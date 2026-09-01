from manim import *

class HairyBallTheorem(Scene):
    def construct(self):
        # Title
        title = Tex("Hairy Ball Theorem", font_size=48)
        self.play(Write(title))
        self.wait(2)
        self.play(FadeOut(title))

        # 3D Sphere
        sphere = Sphere(radius=2, resolution=(64, 32))
        sphere.set_shade_in_3d(True)
        self.play(Create(sphere), run_time=3)
        self.camera.rotate(angle=TAU / 4, axis=UP)
        self.wait(2)

        # Vector Field
        num_vectors = 50
        vectors = VGroup()
        for i in range(num_vectors):
            angle1 = random.uniform(0, TAU)
            angle2 = random.uniform(0, PI)
            x = sphere.radius * np.sin(angle2) * np.cos(angle1)
            y = sphere.radius * np.sin(angle2) * np.sin(angle1)
            z = sphere.radius * np.cos(angle2)
            vector_point = Point3D(x, y, z)
            vector = Arrow3D(vector_point, vector_point + sphere.normal.copy().rotate(angle1, axis=UP) * 0.3, buff=0)
            vectors.add(vector)
        self.play(Create(vectors), run_time=3)
        self.wait(2)

        # Combing Process
        self.play(
            Rotate(vectors, angle=TAU / 2, axis=UP, run_time=5),
            self.camera.rotate(angle=TAU / 4, axis=UP)
        )
        self.wait(2)

        # Bald Spot - approximate location
        bald_spot = Point3D(0, 0, sphere.radius)
        bald_spot_marker = Circle(radius=0.1, color=RED)
        bald_spot_marker.move_to(bald_spot)
        self.play(Create(bald_spot_marker), run_time=2)

        # Highlight Bald Spot
        self.play(
            vectors.animate.set_color(BLUE).shift(DOWN * 0.5),
            bald_spot_marker.animate.set_color(YELLOW).scale(1.5)
        )
        self.wait(3)

        # Explanation
        explanation = Tex("At least one 'bald spot' must exist.", font_size=24)
        explanation.move_to(DOWN * 3)
        self.play(Write(explanation))
        self.wait(3)

        self.play(FadeOut(sphere, vectors, bald_spot_marker, explanation))
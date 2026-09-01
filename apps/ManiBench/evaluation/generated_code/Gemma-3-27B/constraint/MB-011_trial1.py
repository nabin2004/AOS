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
            vector = Arrow3D(vector_point, vector_point + sphere.radius * 0.2 * np.array([np.cos(angle1), np.sin(angle1), 0]), buff=0)
            vectors.add(vector)
        self.play(Create(vectors), run_time=3)
        self.wait(2)

        # Combing Process
        self.play(
            vectors.animate.shift(DOWN * 0.5 + LEFT * 0.5).run_time(5)
        )
        self.wait(2)

        # Bald Spot
        bald_spot = Dot(sphere.point_from_proportion(0.75), color=RED, size=0.1)
        bald_spot_circle = Circle(radius=0.2, color=RED, stroke_width=2, fill_opacity=0.2)
        bald_spot_circle.move(sphere.point_from_proportion(0.75))
        self.play(Create(bald_spot_circle), Create(bald_spot))
        self.wait(2)

        # Highlight Bald Spot
        self.play(
            vectors.animate.set_color(BLUE).run_time(2),
            bald_spot.animate.scale(1.5).run_time(2),
            bald_spot_circle.animate.scale(1.2).run_time(2)
        )
        self.wait(3)

        # Explanation
        explanation = Tex("The Hairy Ball Theorem states that you cannot comb the hairs on a sphere without creating a bald spot.", font_size=24)
        explanation.move(DOWN * 2)
        self.play(Write(explanation))
        self.wait(5)

        self.play(FadeOut(sphere, vectors, bald_spot, bald_spot_circle, explanation))
        self.wait(1)
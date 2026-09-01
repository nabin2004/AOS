from manim import *

class HairyBallTheorem(Scene):
    def construct(self):
        # Title
        title = Text("Hairy Ball Theorem", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        # Create 3D axes
        axes = ThreeDAxes()
        self.add(axes)

        # Create sphere
        sphere = Sphere(radius=2, resolution=(10, 10)).set_fill(BLUE, opacity=0.7)
        self.play(Create(sphere))
        self.wait(1)

        # Create vector field
        def vector_field_func(point):
            x, y, z = point
            norm = np.sqrt(x**2 + y**2 + z**2)
            if norm == 0:
                return np.array([0, 0, 0])
            else:
                return np.array([x/norm, y/norm, z/norm])

        vector_field = ArrowVectorField(
            vector_field_func,
            x_range=[-2, 2],
            y_range=[-2, 2],
            z_range=[-2, 2],
            length_func=lambda l: 0.2,
            max_magnitude=1,
            color=YELLOW
        )
        self.play(Create(vector_field))
        self.wait(1)

        # Rotate camera to show vector field
        self.play(Rotate(axes, angle=PI/2, axis=UP))
        self.wait(1)

        # Show combing failure
        combing_text = Text("Combing Failure", font_size=36).to_edge(UP)
        self.play(Write(combing_text))
        
        # Highlight bald spot
        bald_spot = Dot(color=RED).move_to(np.array([0, 0, 0]))
        self.play(Create(bald_spot))
        self.wait(1)

        # Clear scene
        self.clear()
        self.wait(1)

        # Conclusion
        conclusion = Text("A continuous vector field on a 2-sphere\nmust have at least one point where the vector is zero.", font_size=36)
        self.play(Write(conclusion))
        self.wait(2)
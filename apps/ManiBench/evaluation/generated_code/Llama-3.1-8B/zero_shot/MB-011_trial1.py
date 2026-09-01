from manim import *

class HairyBallTheorem(Scene):
    def construct(self):
        # Create a 3D sphere
        sphere = Sphere(radius=2, resolution=64).scale(1.5).shift(UP)

        # Create a vector field
        vector_field = []
        for i in range(64):
            for j in range(64):
                angle = i * PI / 32
                theta = j * PI / 32
                x = 2 * sin(theta) * cos(angle)
                y = 2 * sin(theta) * sin(angle)
                z = 2 * cos(theta)
                vector = 0.1 * (x * RIGHT + y * UP + z * OUT)
                vector_field.append(vector)

        # Create a 3D vector field
        vector_field_3d = []
        for i in range(64):
            for j in range(64):
                vector = vector_field[i * 64 + j]
                x = 2 * sin(j * PI / 32) * cos(i * PI / 32)
                y = 2 * sin(j * PI / 32) * sin(i * PI / 32)
                z = 2 * cos(j * PI / 32)
                vector_3d = Arrow3D(
                    start=ORIGIN,
                    end=vector * 0.1 * (x * RIGHT + y * UP + z * OUT),
                    color=WHITE,
                    buff=0,
                )
                vector_field_3d.append(vector_3d)

        # Create a 3D vector field with a bald spot
        bald_spot_vector_field = []
        for i in range(64):
            for j in range(64):
                if i == 32 and j == 32:
                    vector = 0
                else:
                    vector = vector_field[i * 64 + j]
                x = 2 * sin(j * PI / 32) * cos(i * PI / 32)
                y = 2 * sin(j * PI / 32) * sin(i * PI / 32)
                z = 2 * cos(j * PI / 32)
                vector_3d = Arrow3D(
                    start=ORIGIN,
                    end=vector * 0.1 * (x * RIGHT + y * UP + z * OUT),
                    color=WHITE,
                    buff=0,
                )
                bald_spot_vector_field.append(vector_3d)

        # Animate the vector field
        self.add(sphere)
        self.play(
            AnimationGroup(
                *[FadeIn(vector) for vector in vector_field_3d],
                lag_ratio=0.01,
            ),
            run_time=2,
        )

        # Attempt to orient all vectors continuously
        self.play(
            AnimationGroup(
                *[vector.animate.shift(vector.get_end()) for vector in vector_field_3d],
                lag_ratio=0.01,
            ),
            run_time=2,
        )

        # Show that this is impossible: at least one point must have zero vector (bald spot)
        self.play(
            AnimationGroup(
                *[vector.animate.shift(vector.get_end()) for vector in bald_spot_vector_field],
                lag_ratio=0.01,
            ),
            run_time=2,
        )

        # Animate the 'combing' process, showing where tangency requirements fail
        self.play(
            AnimationGroup(
                *[vector.animate.shift(vector.get_end()) for vector in bald_spot_vector_field],
                lag_ratio=0.01,
            ),
            run_time=2,
        )

        # Highlight the bald spot with a special visual marker
        bald_spot_marker = Dot(
            point=ORIGIN,
            radius=0.1,
            color=RED,
            fill_opacity=1,
        )
        self.add(bald_spot_marker)
        self.play(
            AnimationGroup(
                *[vector.animate.shift(vector.get_end()) for vector in bald_spot_vector_field],
                lag_ratio=0.01,
            ),
            run_time=2,
        )
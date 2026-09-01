from manim import *

class HairyBallTheorem(Scene):
    def construct(self):
        # Set up 3D axes and camera
        axes = ThreeDAxes()
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)

        # Create a sphere
        sphere = Sphere(radius=2, resolution=(24, 24))
        sphere.set_fill(BLUE_E, opacity=0.1)
        sphere.set_stroke(BLUE_E, opacity=0.5)

        # Title
        title = Text("The Hairy Ball Theorem", font_size=36).to_edge(UP)
        theorem_text = MathTex(
            r"\text{No nonvanishing continuous }",
            r"\text{tangent vector field on } S^2"
        ).next_to(title, DOWN)
        self.add_fixed_in_frame_mobjects(title, theorem_text)
        self.play(Write(title), Write(theorem_text))
        self.wait(1)

        # Show sphere
        self.play(Create(sphere), run_time=2)
        self.begin_ambient_camera_rotation(rate=0.1)

        # Function to generate tangent vectors on sphere
        def get_tangent_field(sphere, density=6):
            vectors = VGroup()
            for u in np.linspace(0, PI, density):
                for v in np.linspace(0, TAU, density):
                    if u == 0 or u == PI:  # Skip poles for now
                        continue
                    # Point on sphere
                    x = 2 * np.sin(u) * np.cos(v)
                    y = 2 * np.sin(u) * np.sin(v)
                    z = 2 * np.cos(u)
                    point = np.array([x, y, z])

                    # Tangent vector: try to make it "horizontal" (azimuthal)
                    tangent = np.array([-y, x, 0])  # Circular around z-axis
                    norm_tangent = np.linalg.norm(tangent)
                    if norm_tangent > 1e-5:
                        tangent = tangent / norm_tangent * 0.3  # Normalize and scale
                    else:
                        tangent = np.array([0, 0, 0])

                    arrow = Arrow3D(point, point + tangent, color=YELLOW, stroke_width=2)
                    vectors.add(arrow)
            return vectors

        # Step 1: Show attempted vector field (with flaw at poles)
        vector_field = get_tangent_field(sphere, density=8)
        field_label = Text("Attempting a continuous tangent vector field", font_size=24)
        field_label.next_to(theorem_text, DOWN)
        self.add_fixed_in_frame_mobjects(field_label)
        self.play(FadeIn(field_label), Create(vector_field), run_time=3)
        self.wait(2)

        # Show problem at north pole
        pole_problem_text = Text("Problem at poles!", font_size=24, color=RED)
        pole_problem_text.next_to(field_label, DOWN)
        self.add_fixed_in_frame_mobjects(pole_problem_text)
        self.play(Write(pole_problem_text))

        # Zoom in near north pole
        north_pole = np.array([0, 0, 2])
        self.play(
            self.camera.frame.animate.move_to(north_pole).set_z(1),
            run_time=2
        )
        self.wait(1)

        # Show vectors near north pole becoming small or conflicting
        close_vectors = VGroup()
        for v in vector_field:
            if np.linalg.norm(v.get_start() - north_pole) < 1.0:
                close_vectors.add(v)

        self.play(Indicate(close_vectors, color=RED, scale_factor=1.5), run_time=2)
        self.wait(1)

        # Highlight bald spot at north pole
        bald_spot = Dot3D(north_pole, color=RED, radius=0.1)
        bald_label = Text("Bald Spot (Zero Vector)", font_size=20, color=RED).next_to(bald_spot, RIGHT)
        bald_label.shift(OUT * 2)
        self.add_fixed_orientation_mobjects(bald_label)
        self.play(
            GrowFromCenter(bald_spot),
            Write(bald_label),
            run_time=1.5
        )
        self.wait(2)

        # Explain why it fails
        explanation = VGroup(
            Text("At the pole, direction is undefined", font_size=20, color=YELLOW),
            Text("All directions are equivalent", font_size=20, color=YELLOW),
            Text("→ Vector must vanish", font_size=20, color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT)
        explanation.to_corner(DR)
        self.add_fixed_in_frame_mobjects(explanation)
        self.play(Write(explanation[0]))
        self.wait(1)
        self.play(Write(explanation[1]))
        self.wait(1)
        self.play(Write(explanation[2]))
        self.wait(2)

        # Final conclusion
        conclusion = Text("Thus, at least one 'bald spot' must exist!", font_size=28, color=PURPLE)
        conclusion.to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(conclusion)
        self.play(Write(conclusion))
        self.wait(3)

        # End animation
        self.stop_ambient_camera_rotation()
        self.play(
            FadeOut(explanation),
            FadeOut(conclusion),
            FadeOut(field_label),
            FadeOut(pole_problem_text),
            FadeOut(bald_label),
            FadeOut(title),
            FadeOut(theorem_text),
            run_time=2
        )
        self.wait(1)
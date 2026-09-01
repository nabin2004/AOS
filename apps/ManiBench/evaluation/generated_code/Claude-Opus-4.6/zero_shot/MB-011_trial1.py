from manim import *
import numpy as np


class HairyBallTheorem(ThreeDScene):
    def play_no_lag(self, *args, **kwargs):
        self.play(*args, **kwargs)

    def construct(self):
        # Title
        title = Text("The Hairy Ball Theorem", font_size=42).to_edge(UP)
        subtitle = Text(
            "A continuous tangent vector field on S² must have a zero",
            font_size=24,
        ).next_to(title, DOWN, buff=0.2)

        self.play(Write(title), run_time=1.5)
        self.play(FadeIn(subtitle), run_time=1)
        self.wait(1)
        self.play(FadeOut(title), FadeOut(subtitle))

        # Set up 3D camera
        self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES)

        # Create sphere
        sphere = Surface(
            lambda u, v: np.array([
                np.cos(u) * np.cos(v),
                np.cos(u) * np.sin(v),
                np.sin(u),
            ]),
            u_range=[-PI / 2, PI / 2],
            v_range=[0, TAU],
            resolution=(24, 48),
            fill_opacity=0.3,
            stroke_width=0.5,
            stroke_color=BLUE_E,
            fill_color=BLUE_D,
        )

        self.play(Create(sphere), run_time=2)
        self.wait(0.5)

        # Rotate camera to show it's 3D
        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(2)
        self.stop_ambient_camera_rotation()
        self.move_camera(phi=65 * DEGREES, theta=-30 * DEGREES, run_time=1.5)

        # Step 1 label
        step1_text = Text("Step 1: Draw tangent vectors on the sphere", font_size=28)
        step1_text.to_corner(UL).shift(DOWN * 0.5)
        self.add_fixed_in_frame_mobjects(step1_text)
        self.play(Write(step1_text), run_time=1)

        # Function to create tangent vector at a point on sphere
        # Using a vector field that has a zero at the north and south poles
        # v(theta, phi) ~ e_phi (pointing in the azimuthal direction)
        # This field has zeros at the poles

        def tangent_vector_field(lat, lon, scale=0.15):
            """Returns (point_on_sphere, tangent_vector) for given latitude and longitude."""
            # Point on sphere
            x = np.cos(lat) * np.cos(lon)
            y = np.cos(lat) * np.sin(lon)
            z = np.sin(lat)
            point = np.array([x, y, z])

            # Tangent vector in the azimuthal (e_phi) direction
            # e_phi = (-sin(lon), cos(lon), 0)
            # Scale by cos(lat) to make it go to zero at poles naturally
            magnitude = np.cos(lat)
            tx = -np.sin(lon) * magnitude
            ty = np.cos(lon) * magnitude
            tz = 0.0
            tangent = np.array([tx, ty, tz]) * scale

            return point, tangent

        # Create arrows for the vector field
        arrows = VGroup()
        n_lat = 8
        n_lon = 16

        for i in range(n_lat):
            lat = -PI / 2 + PI * (i + 1) / (n_lat + 1)  # Avoid exact poles
            for j in range(n_lon):
                lon = TAU * j / n_lon
                point, tangent = tangent_vector_field(lat, lon, scale=0.18)

                if np.linalg.norm(tangent) > 0.01:
                    arrow = Arrow3D(
                        start=point,
                        end=point + tangent,
                        color=interpolate_color(GREEN, YELLOW, (np.sin(lat) + 1) / 2),
                        thickness=0.01,
                        height=0.08,
                        base_radius=0.03,
                    )
                    arrows.add(arrow)

        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.02), run_time=3)
        self.wait(1)

        self.play(FadeOut(step1_text))

        # Step 2: Show the combing attempt
        step2_text = Text("Step 2: Try to 'comb' the sphere smoothly", font_size=28)
        step2_text.to_corner(UL).shift(DOWN * 0.5)
        self.add_fixed_in_frame_mobjects(step2_text)
        self.play(Write(step2_text), run_time=1)

        # Rotate to show the field
        self.move_camera(phi=45 * DEGREES, theta=-60 * DEGREES, run_time=2)
        self.wait(1)

        # Now animate combing - try to align vectors more uniformly
        # We'll interpolate toward a "uniform" direction, showing it fails at poles
        def combing_vector_field(lat, lon, t, scale=0.18):
            """Interpolate between azimuthal field and attempted uniform field."""
            x = np.cos(lat) * np.cos(lon)
            y = np.cos(lat) * np.sin(lon)
            z = np.sin(lat)
            point = np.array([x, y, z])

            # Original: azimuthal
            magnitude = np.cos(lat)
            tx0 = -np.sin(lon) * magnitude
            ty0 = np.cos(lon) * magnitude
            tz0 = 0.0
            v0 = np.array([tx0, ty0, tz0])

            # Target: try to comb everything "to the right" (x-direction projected tangent)
            # Project x-hat onto tangent plane: x_hat - (x_hat . n) * n
            normal = point
            x_hat = np.array([1.0, 0.0, 0.0])
            x_tangent = x_hat - np.dot(x_hat, normal) * normal
            norm_xt = np.linalg.norm(x_tangent)
            if norm_xt > 1e-6:
                x_tangent = x_tangent / norm_xt
            else:
                x_tangent = np.array([0.0, 0.0, 0.0])

            v1 = x_tangent

            # Interpolate
            v = (1 - t) * v0 + t * v1
            tangent = v * scale

            return point, tangent

        # Animate the combing process in steps
        n_steps = 5
        for step in range(1, n_steps + 1):
            t = step / n_steps
            new_arrows = VGroup()

            for i in range(n_lat):
                lat = -PI / 2 + PI * (i + 1) / (n_lat + 1)
                for j in range(n_lon):
                    lon = TAU * j / n_lon
                    point, tangent = combing_vector_field(lat, lon, t, scale=0.18)

                    mag = np.linalg.norm(tangent)
                    if mag > 0.005:
                        color = interpolate_color(GREEN, RED, 1.0 - min(mag / 0.18, 1.0))
                        arrow = Arrow3D(
                            start=point,
                            end=point + tangent,
                            color=color,
                            thickness=0.01,
                            height=0.08,
                            base_radius=0.03,
                        )
                    else:
                        # Near-zero vector: show as red dot
                        arrow = Dot3D(point=point, radius=0.04, color=RED)
                    new_arrows.add(arrow)

            self.play(
                ReplacementTransform(arrows, new_arrows),
                run_time=1.5,
            )
            arrows = new_arrows

        self.wait(1)
        self.play(FadeOut(step2_text))

        # Step 3: Show the bald spots
        step3_text = Text(
            "Step 3: Bald spots appear where vectors vanish!", font_size=28
        )
        step3_text.to_corner(UL).shift(DOWN * 0.5)
        self.add_fixed_in_frame_mobjects(step3_text)
        self.play(Write(step3_text), run_time=1)

        # Move camera to show north pole
        self.move_camera(phi=20 * DEGREES, theta=-30 * DEGREES, run_time=2)

        # Create bald spot markers at poles (where the combed field vanishes)
        # North pole bald spot
        north_pole = np.array([1.0, 0.0, 0.0])  # x-hat direction on sphere where field vanishes
        south_pole = np.array([-1.0, 0.0, 0.0])

        # Actually for the "comb to x" field, zeros are at (1,0,0) and (-1,0,0)
        bald_spot_1 = Dot3D(point=north_pole * 1.02, radius=0.08, color=RED)
        bald_spot_2 = Dot3D(point=south_pole * 1.02, radius=0.08, color=RED)

        # Pulsing rings around bald spots
        ring1 = Circle(radius=0.15, color=RED, stroke_width=4)
        ring1.move_to(north_pole * 1.02)
        ring1.rotate(PI / 2, axis=UP)

        ring2 = Circle(radius=0.15, color=RED, stroke_width=4)
        ring2.move_to(south_pole * 1.02)
        ring2.rotate(PI / 2, axis=UP)

        # Labels
        bald_label_1 = Text("Bald Spot!", font_size=22, color=RED)
        bald_label_1.next_to(bald_spot_1, UP + RIGHT, buff=0.3)

        self.play(
            GrowFromCenter(bald_spot_1),
            GrowFromCenter(bald_spot_2),
            run_time=1,
        )

        # Animate pulsing
        self.play(
            Create(ring1),
            Create(ring2),
            run_time=1,
        )

        # Pulse animation
        for _ in range(3):
            self.play(
                ring1.animate.scale(1.5).set_opacity(0),
                ring2.animate.scale(1.5).set_opacity(0),
                run_time=0.8,
            )
            ring1.scale(1 / 1.5).set_opacity(1)
            ring2.scale(1 / 1.5).set_opacity(1)

        self.wait(1)
        self.play(FadeOut(step3_text))

        # Move camera to show both bald spots
        self.move_camera(phi=60 * DEGREES, theta=-90 * DEGREES, run_time=2)
        self.wait(1)

        # Step 4: Explanation
        step4_text = Text(
            "The Hairy Ball Theorem proves this is unavoidable!",
            font_size=28,
            color=YELLOW,
        )
        step4_text.to_corner(UL).shift(DOWN * 0.5)
        self.add_fixed_in_frame_mobjects(step4_text)
        self.play(Write(step4_text), run_time=1.5)
        self.wait(1)

        explanation = VGroup(
            Text("• Any continuous tangent vector field on S²", font_size=22),
            Text("  must vanish at some point", font_size=22),
            Text("• You cannot comb a hairy ball flat", font_size=22),
            Text("  without creating a cowlick!", font_size=22),
            Text("• Related to the Euler characteristic χ(S²) = 2", font_size=22),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        explanation.to_corner(DL).shift(UP * 0.5 + RIGHT * 0.3)

        self.add_fixed_in_frame_mobjects(explanation)
        self.play(
            LaggedStart(*[FadeIn(line, shift=RIGHT * 0.3) for line in explanation], lag_ratio=0.3),
            run_time=3,
        )

        # Final rotation
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(4)
        self.stop_ambient_camera_rotation()

        # Fade everything out
        self.play(
            FadeOut(step4_text),
            FadeOut(explanation),
            FadeOut(arrows),
            FadeOut(sphere),
            FadeOut(bald_spot_1),
            FadeOut(bald_spot_2),
            FadeOut(ring1),
            FadeOut(ring2),
            run_time=2,
        )

        # Final title card
        final_text = VGroup(
            Text("The Hairy Ball Theorem", font_size=42, color=BLUE),
            Text("∀ continuous v: S² → TS², ∃ p ∈ S² : v(p) = 0", font_size=30),
            Text('"You can\'t comb a coconut"', font_size=28, color=YELLOW),
        ).arrange(DOWN, buff=0.4)

        self.add_fixed_in_frame_mobjects(final_text)
        self.play(Write(final_text), run_time=2)
        self.wait(3)
        self.play(FadeOut(final_text), run_time=1.5)
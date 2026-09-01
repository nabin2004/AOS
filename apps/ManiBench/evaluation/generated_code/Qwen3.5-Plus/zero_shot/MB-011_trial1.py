from manim import *
import numpy as np

class HairyBallTheorem(Scene):
    def construct(self):
        # Title
        title = Text("The Hairy Ball Theorem", font_size=40)
        subtitle = Text("No non-vanishing continuous tangent vector field on S²", font_size=24, color=GRAY)
        title_group = VGroup(title, subtitle).arrange(DOWN)
        
        self.play(Write(title), run_time=1.5)
        self.play(FadeIn(subtitle), run_time=1)
        self.wait(1)
        self.play(FadeOut(title_group), shift=UP)

        # Create 3D Sphere
        sphere = Sphere(radius=2.0, resolution=(30, 30))
        sphere.set_stroke(color=BLUE_E, width=1, opacity=0.5)
        sphere.set_fill(color=BLUE_D, opacity=0.2)
        
        # Add a grid to make rotation visible
        sphere_grid = Surface(
            lambda u, v: np.array([
                2.0 * np.cos(u) * np.cos(v),
                2.0 * np.sin(u) * np.cos(v),
                2.0 * np.sin(v)
            ]),
            u_range=[0, 2 * PI],
            v_range=[-PI / 2, PI / 2],
            resolution=(20, 10),
            stroke_color=WHITE,
            stroke_width=0.5,
            fill_opacity=0.1
        )

        # Set up 3D camera
        self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.8)
        
        # Animate sphere appearance
        self.play(Create(sphere), Create(sphere_grid), run_time=2)
        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(2)

        # Label the sphere
        sphere_label = Text("2-Sphere (S²)", font_size=24).to_corner(UR)
        self.add_fixed_in_frame_mobjects(sphere_label)
        self.play(Write(sphere_label))

        # Stop rotation for vector field demonstration
        self.stop_ambient_camera_rotation()
        
        # Function to generate tangent vectors (simulating "hair")
        # We will use a "comb" attempt that fails at the poles
        def get_hair_vector(u, v, scale=0.4):
            # Position on sphere
            x = 2.0 * np.cos(u) * np.cos(v)
            y = 2.0 * np.sin(u) * np.cos(v)
            z = 2.0 * np.sin(v)
            point = np.array([x, y, z])
            
            # Normal vector
            normal = point / np.linalg.norm(point)
            
            # Attempt 1: Try to comb from South to North (Longitudinal)
            # Tangent vector pointing North
            tangent = np.array([-np.cos(u)*np.sin(v), -np.sin(u)*np.sin(v), np.cos(v)])
            tangent = tangent / np.linalg.norm(tangent) * scale
            
            # At poles (v = +/- pi/2), this vector becomes zero or undefined directionally in limit
            # But visually, we want to show the "swirl" or the zero point.
            # Let's create a field that looks like it's being combed upwards.
            
            return point, tangent

        # Create VGroup for hairs
        hairs = VGroup()
        u_steps = 12
        v_steps = 8
        
        # Generate initial hairs (Longitudinal flow)
        for i in range(u_steps):
            for j in range(v_steps):
                u = (i / u_steps) * 2 * PI
                v = -PI/2 + (j / v_steps) * PI + (PI/(2*v_steps)) # Avoid exact poles initially
                
                pos, vec = get_hair_vector(u, v)
                
                # Create arrow
                arrow = Arrow3D(
                    start=pos,
                    end=pos + vec,
                    thickness=0.02,
                    color=YELLOW
                )
                hairs.add(arrow)

        self.play(LaggedStart(*[Create(h) for h in hairs], lag_ratio=0.05), run_time=3)
        self.wait(1)

        # Explanation Text
        explanation1 = Text("Attempt 1: Comb from South to North", font_size=24)
        self.add_fixed_in_frame_mobjects(explanation1)
        explanation1.to_edge(DOWN)
        self.play(Write(explanation1))
        self.wait(2)

        # Highlight the problem at the North Pole
        north_pole = Dot3D(point=np.array([0, 0, 2.0]), color=RED, radius=0.15)
        pole_label = Text("Singularity!", color=RED, font_size=20).next_to(north_pole, RIGHT)
        self.add_fixed_in_frame_mobjects(pole_label)
        
        # Move camera to focus on North Pole
        self.move_camera(phi=45 * DEGREES, theta=0 * DEGREES, zoom=1.2, run_time=2)
        
        self.play(Create(north_pole), Write(pole_label))
        self.wait(1)
        
        # Show that vectors shrink to zero at the pole
        # We simulate this by fading out hairs near the pole and showing the gap
        top_hairs = VGroup()
        for h in hairs:
            if h.get_end()[2] > 1.5: # Near north pole
                top_hairs.add(h)
        
        self.play(top_hairs.animate.set_opacity(0.2), run_time=1)
        self.wait(1)

        # Reset and try a different combing (Rotational/Swirl)
        self.play(FadeOut(explanation1), FadeOut(north_pole), FadeOut(pole_label))
        self.move_camera(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.8, run_time=2)
        
        explanation2 = Text("Attempt 2: Rotational Flow (Swirl)", font_size=24)
        self.add_fixed_in_frame_mobjects(explanation2)
        explanation2.to_edge(DOWN)
        self.play(Write(explanation2))

        # Transform hairs to rotational field
        # f(u, v) -> tangent along latitude
        new_hairs = VGroup()
        for i in range(u_steps):
            for j in range(v_steps):
                u = (i / u_steps) * 2 * PI
                v = -PI/2 + (j / v_steps) * PI + (PI/(2*v_steps))
                
                x = 2.0 * np.cos(u) * np.cos(v)
                y = 2.0 * np.sin(u) * np.cos(v)
                z = 2.0 * np.sin(v)
                pos = np.array([x, y, z])
                
                # Tangent vector along latitude (Eastward)
                # Derivative w.r.t u is (-sin(u)cos(v), cos(u)cos(v), 0)
                vec = np.array([-np.sin(u), np.cos(u), 0]) * np.cos(v) # Scale by cos(v) to shrink at poles
                vec = vec / (np.linalg.norm(vec) + 1e-6) * 0.4 * np.cos(v) # Shrink explicitly
                
                arrow = Arrow3D(
                    start=pos,
                    end=pos + vec,
                    thickness=0.02,
                    color=GREEN
                )
                new_hairs.add(arrow)

        # Animate transition
        self.play(
            ReplacementTransform(hairs, new_hairs),
            run_time=3
        )
        self.wait(1)

        # Highlight problems at BOTH poles now
        south_pole = Dot3D(point=np.array([0, 0, -2.0]), color=RED, radius=0.15)
        north_pole_2 = Dot3D(point=np.array([0, 0, 2.0]), color=RED, radius=0.15)
        
        label_n = Text("Bald Spot", color=RED, font_size=20).next_to(north_pole_2, UP)
        label_s = Text("Bald Spot", color=RED, font_size=20).next_to(south_pole, DOWN)
        
        self.add_fixed_in_frame_mobjects(label_n, label_s)
        
        self.play(
            Create(north_pole_2), Create(south_pole),
            Write(label_n), Write(label_s),
            run_time=2
        )
        self.wait(2)

        # Final Conclusion
        self.stop_ambient_camera_rotation()
        self.move_camera(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.6, run_time=2)
        
        self.play(FadeOut(explanation2), FadeOut(new_hairs), FadeOut(sphere_grid), FadeOut(label_n), FadeOut(label_s))
        self.play(sphere.animate.set_fill(color=GREY, opacity=0.5).set_stroke(width=0.5))
        
        # Show the theorem statement clearly
        final_text = VGroup(
            Text("The Hairy Ball Theorem", font_size=36, color=WHITE),
            Text("Any continuous tangent vector field", font_size=24, color=WHITE),
            Text("on a 2-sphere must have a zero.", font_size=24, color=WHITE),
            Text("χ(S²) = 2 ≠ 0", font_size=24, color=YELLOW) # Euler characteristic hint
        ).arrange(DOWN, buff=0.3)
        
        final_text.set_stroke(color=BLACK, width=2, background=True)
        self.add_fixed_in_frame_mobjects(final_text)
        final_text.move_to(ORIGIN)
        
        # Add a visual marker for the "Bald Spot" on a clean sphere
        bald_spot_marker = Dot3D(point=np.array([0, 0, 2.0]), color=RED, radius=0.2)
        marker_label = Text("Necessarily Zero Here", color=RED, font_size=24).next_to(bald_spot_marker, RIGHT)
        self.add_fixed_in_frame_mobjects(marker_label)
        
        self.play(
            FadeIn(final_text),
            Create(bald_spot_marker),
            Write(marker_label),
            run_time=3
        )
        
        self.begin_ambient_camera_rotation(rate=0.1)
        self.wait(4)
        self.stop_ambient_camera_rotation()
from manim import *

class HairyBallTheorem(ThreeDScene):
    """
    An animation demonstrating the Hairy Ball Theorem.
    This theorem states that any continuous tangent vector field on a sphere
    must have at least one point with a zero vector (a "bald spot").
    """

    def construct(self):
        # 1. Introduction and Scene Setup
        title = Text("The Hairy Ball Theorem", font_size=48).to_corner(UL)
        self.add_fixed_in_frame_mobjects(title)

        # Set up 3D axes for context and orient the camera
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)

        self.play(Write(title))
        self.wait()

        # 2. Create the Sphere
        sphere = Sphere(
            radius=2,
            resolution=(24, 48),
            fill_opacity=0.7,
            checkerboard_colors=[BLUE_D, BLUE_E]
        )
        sphere_label = Text("Consider a sphere...").next_to(title, DOWN, buff=0.5)
        self.add_fixed_in_frame_mobjects(sphere_label)

        self.play(Create(sphere), Write(sphere_label))
        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(2)
        self.play(FadeOut(sphere_label))

        # 3. Define and Animate the Vector Field ("Combing the Hair")
        
        # This vector field function attempts to "comb" the hair horizontally.
        # V(x, y, z) is defined as the cross product of the position vector P=(x,y,z)
        # and a fixed vector (e.g., k_hat = [0,0,1]).
        # The resulting vector V is always tangent to the sphere because V is perpendicular to P.
        # However, at the poles, P is parallel to k_hat, so their cross product is the zero vector.
        def combing_func(point):
            fixed_vector = OUT  # This is k_hat or [0, 0, 1]
            vector = np.cross(point, fixed_vector)
            # At the poles, the position vector is parallel to the fixed_vector,
            # so the cross product (the tangent vector) is zero.
            return vector

        # Create the vector field mobject using a helper function
        vector_field = self.get_vector_field(sphere, combing_func, vector_length=0.5)

        combing_label = Text("...and cover it with a continuous tangent vector field.", t2w={'tangent': BOLD}).next_to(title, DOWN, buff=0.5)
        self.add_fixed_in_frame_mobjects(combing_label)
        self.play(Write(combing_label))

        # Animate the creation of the vector field, showing the "combing"
        self.play(LaggedStart(*[Create(vec) for vec in vector_field], lag_ratio=0.05, run_time=4))
        self.wait(3)

        self.play(FadeOut(combing_label))
        self.stop_ambient_camera_rotation()

        # 4. Highlight the Inevitable "Bald Spot"
        bald_spot_label = Text("This combing attempt reveals a 'bald spot'!", color=YELLOW).next_to(title, DOWN, buff=0.5)
        self.add_fixed_in_frame_mobjects(bald_spot_label)
        self.play(Write(bald_spot_label))

        # Move camera to focus on the North Pole where the vectors are zero
        self.move_camera(phi=10 * DEGREES, theta=0 * DEGREES, zoom=2.5, run_time=3)

        # Create a visual marker for the bald spot
        north_pole_point = sphere.get_top()
        bald_spot_marker = Dot3D(point=north_pole_point, color=RED, radius=0.1)
        
        # Create an arrow and text pointing to the marker in 3D space
        label_pos = north_pole_point + np.array([0.8, 0.8, 0.5])
        bald_spot_text = Text("Bald Spot\n(zero vector)", font_size=24).move_to(label_pos)
        bald_spot_text.add_background_rectangle(opacity=0.7, buff=0.1)
        
        arrow_to_spot = Arrow3D(
            start=label_pos + bald_spot_text.get_width() / 2 * LEFT,
            end=north_pole_point + 0.1 * OUT, # Point just above the surface
            color=YELLOW,
            thickness=0.01,
            height=0.2
        )

        self.play(FadeIn(bald_spot_marker, scale=1.5))
        self.play(GrowArrow(arrow_to_spot), Write(bald_spot_text))
        self.play(Flash(bald_spot_marker, color=YELLOW, line_length=0.3, num_lines=12, run_time=2))
        self.wait(3)

        # 5. State the Theorem Formally
        self.move_camera(phi=75 * DEGREES, theta=30 * DEGREES, zoom=1, run_time=3)
        
        theorem_group = VGroup(bald_spot_marker, arrow_to_spot, bald_spot_text)
        self.play(FadeOut(theorem_group, bald_spot_label))
        
        theorem_text = VGroup(
            Text("Theorem:", weight=BOLD),
            Text("Any continuous tangent vector field on a sphere", t2w={'tangent': BOLD}),
            Text("must have at least one point where the vector is zero."),
        ).arrange(DOWN, center=False, aligned_edge=LEFT).scale(0.8).next_to(title, DOWN, buff=0.5)
        theorem_text.add_background_rectangle_to_submobjects(opacity=0.8, buff=0.2)

        self.add_fixed_in_frame_mobjects(theorem_text)
        self.play(Write(theorem_text))
        self.begin_ambient_camera_rotation(rate=0.1)
        self.wait(8)

        # Fade out all elements for a clean exit
        self.play(
            FadeOut(title),
            FadeOut(theorem_text),
            FadeOut(vector_field),
            FadeOut(sphere),
            run_time=2
        )
        self.wait()

    def get_vector_field(self, surface, func, **kwargs):
        """
        Generates a VGroup of vectors on a given surface.
        
        Args:
            surface: The Manim Surface mobject.
            func: A function that takes a 3D point and returns a 3D vector.
            **kwargs: Keyword arguments for vector styling.
        
        Returns:
            A VGroup containing all the Arrow3D mobjects.
        """
        vector_length = kwargs.get("vector_length", 0.5)
        
        # Define the density of vectors on the surface
        nu = 24  # Number of vectors along longitude
        nv = 12  # Number of vectors along latitude
        
        vectors = VGroup()
        
        # Iterate over the parametric coordinates (u, v) of the surface
        # We skip the very first and last latitude lines to avoid the poles,
        # where the vector is zero and might cause normalization issues.
        # The absence of arrows at the poles visually represents the "bald spot".
        u_range = surface.u_range
        v_range = surface.v_range
        v_step = (v_range[1] - v_range[0]) / (nv + 1)

        for i in range(nu):
            for j in range(1, nv + 1):
                u = u_range[0] + i * (u_range[1] - u_range[0]) / nu
                v = v_range[0] + j * v_step
                
                point = surface.get_point_from_uv([u, v])
                vector = func(point)
                
                # Only draw an arrow if the vector has a non-zero magnitude
                if np.linalg.norm(vector) > 1e-6:
                    # Normalize and scale the vector for consistent visualization
                    scaled_vector = vector / np.linalg.norm(vector) * vector_length
                    arrow = Arrow3D(
                        start=point,
                        end=point + scaled_vector,
                        thickness=0.006,
                        height=0.15,
                        base_radius=0.04,
                        color=YELLOW
                    )
                    vectors.add(arrow)
        return vectors
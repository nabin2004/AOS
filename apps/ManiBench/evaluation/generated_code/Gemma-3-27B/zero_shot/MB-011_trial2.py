from manim import *

class HairyBallTheorem(Scene):
    def construct(self):
        # 1. 3D Sphere with Rotation
        sphere = Sphere(radius=2, resolution=(32, 32))
        sphere.set_fill(BLUE_E, opacity=0.5)
        self.play(Create(sphere))
        self.play(Rotate(sphere, angle=TAU, axis=Z, run_time=5))

        # 2. Vector Field
        num_vectors = 100
        vectors = VGroup(*[Arrow(radius=0.2, color=YELLOW) for _ in range(num_vectors)])
        
        def get_vector_direction(angle1, angle2):
            x = np.sin(angle1) * np.cos(angle2)
            y = np.sin(angle1) * np.sin(angle2)
            z = np.cos(angle1)
            return np.array([x, y, z])

        def map_to_sphere(point):
            return point / np.linalg.norm(point)

        for vector in vectors:
            angle1 = np.random.uniform(0, TAU)
            angle2 = np.random.uniform(0, TAU)
            direction = get_vector_direction(angle1, angle2)
            
            # Project direction onto sphere
            direction = map_to_sphere(direction)
            
            vector.set_angle(UP, direction)
            vector.move_to(sphere.point_from_angle(angle1, angle2))

        self.play(Create(vectors))

        # 3. Attempt Continuous Orientation
        self.play(
            vectors.animate.shift(DOWN * 0.5).scale(0.8)
        )
        
        # 4. Show Impossibility - Bald Spot
        bald_spot = Dot(radius=0.1, color=RED)
        bald_spot.move_to(sphere.point_from_angle(0, 0))  # Example bald spot
        
        self.play(Create(bald_spot))
        self.play(
            Indicate(bald_spot, color=RED, scale_factor=1.5)
        )
        
        text_bald_spot = Text("Bald Spot", color=RED)
        text_bald_spot.next_to(bald_spot, UP)
        self.play(Write(text_bald_spot))

        # 5. Animate 'Combing' Process (Simplified)
        # This is a simplification, a full demonstration would be complex
        
        # Create a circle to represent a 'comb'
        comb = Circle(radius=0.5, color=GREEN)
        comb.move_to(sphere.point_from_angle(TAU / 4, 0))
        self.play(Create(comb))
        
        # Animate the comb moving around the sphere
        self.play(
            Rotate(comb, angle=TAU, axis=Z, run_time=3)
        )
        
        # Highlight the failure of tangency
        failure_point = Dot(radius=0.1, color=ORANGE)
        failure_point.move_to(sphere.point_from_angle(TAU / 2, 0))
        self.play(Create(failure_point))
        
        text_failure = Text("Tangency Failure", color=ORANGE)
        text_failure.next_to(failure_point, UP)
        self.play(Write(text_failure))

        # 6. Highlight Bald Spot
        self.play(
            Indicate(bald_spot, color=RED, scale_factor=2)
        )
        
        self.wait(2)
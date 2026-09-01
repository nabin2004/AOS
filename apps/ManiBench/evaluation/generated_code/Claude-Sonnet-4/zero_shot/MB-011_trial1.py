from manim import *
import numpy as np

class HairyBallTheorem(ThreeDScene):
    def construct(self):
        # Set up 3D scene
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
        
        # Create sphere
        sphere = Sphere(radius=2, resolution=(20, 20))
        sphere.set_color(BLUE)
        sphere.set_opacity(0.3)
        
        # Title
        title = Text("Hairy Ball Theorem", font_size=48)
        title.to_edge(UP)
        
        self.add_fixed_in_frame_mobjects(title)
        self.play(Write(title))
        self.play(Create(sphere))
        
        # Create vector field on sphere
        vectors = VGroup()
        vector_origins = []
        
        # Generate points on sphere surface
        phi_vals = np.linspace(0, PI, 8)
        theta_vals = np.linspace(0, 2*PI, 12)
        
        for phi in phi_vals[1:-1]:  # Exclude poles initially
            for theta in theta_vals[:-1]:  # Avoid duplicate at 2π
                # Spherical coordinates to Cartesian
                x = 2 * np.sin(phi) * np.cos(theta)
                y = 2 * np.sin(phi) * np.sin(theta)
                z = 2 * np.cos(phi)
                origin = np.array([x, y, z])
                vector_origins.append(origin)
                
                # Create tangent vector (initially pointing in theta direction)
                tangent_x = -np.sin(theta)
                tangent_y = np.cos(theta)
                tangent_z = 0
                tangent = 0.3 * np.array([tangent_x, tangent_y, tangent_z])
                
                vector = Arrow3D(
                    start=origin,
                    end=origin + tangent,
                    color=RED,
                    thickness=0.02,
                    height=0.1,
                    base_radius=0.05
                )
                vectors.add(vector)
        
        # Add vectors to scene
        self.play(Create(vectors), run_time=2)
        
        # Add explanation text
        explanation1 = Text("Vector field on sphere surface", font_size=32)
        explanation1.to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(explanation1)
        self.play(Write(explanation1))
        
        # Rotate camera to show 3D nature
        self.play(
            Rotate(sphere, angle=PI/3, axis=UP),
            Rotate(vectors, angle=PI/3, axis=UP),
            run_time=2
        )
        
        # Show combing attempt
        self.play(FadeOut(explanation1))
        explanation2 = Text("Attempting to 'comb' vectors smoothly...", font_size=32)
        explanation2.to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(explanation2)
        self.play(Write(explanation2))
        
        # Animate combing process - vectors trying to align
        new_vectors = VGroup()
        for i, origin in enumerate(vector_origins):
            phi_idx = i // 11  # Approximate phi index
            theta_idx = i % 11  # Approximate theta index
            
            # Create a "combed" vector field that will have issues at poles
            if phi_idx < 3:  # Upper hemisphere
                direction = np.array([1, 0, 0])  # Try to point east
            else:  # Lower hemisphere  
                direction = np.array([-1, 0, 0])  # Point west
            
            # Make vector tangent to sphere
            normal = origin / np.linalg.norm(origin)
            direction = direction - np.dot(direction, normal) * normal
            if np.linalg.norm(direction) > 0:
                direction = direction / np.linalg.norm(direction)
            
            new_vector = Arrow3D(
                start=origin,
                end=origin + 0.3 * direction,
                color=YELLOW,
                thickness=0.02,
                height=0.1,
                base_radius=0.05
            )
            new_vectors.add(new_vector)
        
        self.play(Transform(vectors, new_vectors), run_time=3)
        
        # Show the problem - add north and south poles
        north_pole = np.array([0, 0, 2])
        south_pole = np.array([0, 0, -2])
        
        # Highlight problematic regions
        problem_north = Sphere(radius=0.3, resolution=(10, 10))
        problem_north.move_to(north_pole)
        problem_north.set_color(RED)
        problem_north.set_opacity(0.7)
        
        problem_south = Sphere(radius=0.3, resolution=(10, 10))
        problem_south.move_to(south_pole)
        problem_south.set_color(RED)
        problem_south.set_opacity(0.7)
        
        self.play(FadeOut(explanation2))
        explanation3 = Text("Contradiction at poles!", font_size=32, color=RED)
        explanation3.to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(explanation3)
        self.play(Write(explanation3))
        
        self.play(
            Create(problem_north),
            Create(problem_south),
            run_time=2
        )
        
        # Show bald spots
        bald_spot_north = Dot3D(point=north_pole, radius=0.1, color=WHITE)
        bald_spot_south = Dot3D(point=south_pole, radius=0.1, color=WHITE)
        
        self.play(FadeOut(explanation3))
        explanation4 = Text("Bald spots: points where vector = 0", font_size=32)
        explanation4.to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(explanation4)
        self.play(Write(explanation4))
        
        self.play(
            Create(bald_spot_north),
            Create(bald_spot_south),
            run_time=2
        )
        
        # Final rotation to show the complete picture
        self.play(
            Rotate(sphere, angle=2*PI, axis=UP),
            Rotate(vectors, angle=2*PI, axis=UP),
            Rotate(problem_north, angle=2*PI, axis=UP),
            Rotate(problem_south, angle=2*PI, axis=UP),
            Rotate(bald_spot_north, angle=2*PI, axis=UP),
            Rotate(bald_spot_south, angle=2*PI, axis=UP),
            run_time=4
        )
        
        # Final explanation
        self.play(FadeOut(explanation4))
        conclusion = Text("Hairy Ball Theorem: Continuous tangent vector field\nmust have at least one zero point", 
                         font_size=28, color=GREEN)
        conclusion.to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(conclusion)
        self.play(Write(conclusion))
        
        self.wait(3)
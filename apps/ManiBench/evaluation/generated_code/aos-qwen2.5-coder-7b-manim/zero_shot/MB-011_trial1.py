from manim import *

class HairyBallTheorem(Scene):
    def construct(self):
        # Title
        title = Text("Hairy Ball Theorem", font_size=36)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        # Create 3D axes
        axes = ThreeDAxes(
            x_range=[-2, 2],
            y_range=[-2, 2],
            z_range=[-2, 2],
            axis_config={"color": WHITE}
        )
        
        # Label axes
        x_label = MathTex("x").next_to(axes.x_axis.get_end(), RIGHT)
        y_label = MathTex("y").next_to(axes.y_axis.get_end(), UP)
        z_label = MathTex("z").next_to(axes.z_axis.get_end(), OUT)

        # Add axes to scene
        self.play(Create(axes), Write(x_label), Write(y_label), Write(z_label))
        self.wait(1)

        # Create sphere
        sphere = Sphere(radius=1, resolution=(30, 30)).move_to(ORIGIN)
        sphere.set_fill(BLUE, opacity=0.7)
        sphere.set_stroke(WHITE, width=1)

        # Add sphere to scene
        self.play(Create(sphere))
        self.wait(1)

        # Vector field on sphere
        def vector_field(point):
            # Convert point from spherical to Cartesian coordinates
            r = np.linalg.norm(point)
            theta = np.arccos(point[2] / r)
            phi = np.arctan2(point[1], point[0])
            
            # Compute normal vector using spherical coordinates
            normal_vector = np.array([
                -np.sin(theta) * np.cos(phi),
                -np.sin(theta) * np.sin(phi),
                np.cos(theta)
            ])
            
            # Scale vector for visualization
            return normal_vector * 0.5
        
        # Create vector field
        vectors = ArrowVectorField(vector_field, 
                                  x_range=[-1.8, 1.8],
                                  y_range=[-1.8, 1.8],
                                  z_range=[-1.8, 1.8],
                                  length_func=lambda norm: norm,
                                  max_magnitude=1,
                                  color=WHITE)
        
        # Add vector field to scene
        self.play(Create(vectors))
        self.wait(1)

        # Rotate camera around sphere
        self.play(Rotate(axes, angle=PI/2, about_point=ORIGIN), run_time=2)
        self.wait(1)

        # Combing process visualization
        combing_text = Text("Combing process fails...", font_size=24).to_edge(UP)
        self.play(Write(combing_text))
        
        # Highlight bald spot
        bald_spot = Dot(color=YELLOW, radius=0.1).move_to(np.array([0, 0, 0]))
        self.play(Create(bald_spot))
        
        # Show vector at origin (should be zero)
        origin_vector = vectors.get_vector_at_point(np.array([0, 0, 0]))
        self.play(origin_vector.animate.set_color(RED))
        self.wait(1)

        # Conclusion
        conclusion = Text("At least one point must be bald.", font_size=24).to_edge(UP)
        self.play(Transform(combing_text, conclusion))
        self.wait(2)

        # Fade out everything
        self.play(*[FadeOut(mob) for mob in self.mobjects])
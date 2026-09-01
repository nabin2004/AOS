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

        # Vector field visualization
        num_arrows = 100
        arrow_group = VGroup()

        for _ in range(num_arrows):
            # Random point on sphere
            theta = np.random.uniform(0, 2*np.pi)
            phi = np.arccos(np.random.uniform(-1, 1))
            
            # Convert spherical to Cartesian coordinates
            x = np.sin(phi) * np.cos(theta)
            y = np.sin(phi) * np.sin(theta)
            z = np.cos(phi)
            
            # Position of arrow tip
            tip_pos = np.array([x, y, z]) * 1.1
            
            # Direction vector (tangent to sphere)
            dir_vector = np.array([-x, -y, -z])
            
            # Create arrow
            arrow = Arrow(start=np.array([x, y, z]), end=tip_pos, buff=0, color=YELLOW)
            arrow.add_updater(lambda mobj, dt: mobj.become(Arrow(start=mobj.start, end=mobj.start + dir_vector, buff=0, color=YELLOW)))
            
            # Add to group
            arrow_group.add(arrow)

        # Add vector field to scene
        self.play(LaggedStart(*[GrowArrow(a) for a in arrow_group], lag_ratio=0.01))
        self.wait(1)

        # Combing process visualization
        combing_text = Text("Combing the hair...", font_size=24).to_edge(UP)
        self.play(Write(combing_text))
        
        # Rotate sphere to show combing issues
        self.play(Rotate(sphere, angle=PI/2, about_point=ORIGIN, run_time=2))
        self.wait(1)
        
        # Highlight bald spot
        bald_spot = Dot(point=sphere.get_center() + np.array([0, 0, 0.5]), radius=0.1, color=RED)
        bald_spot_text = Text("Bald Spot", font_size=20).next_to(bald_spot, DOWN)
        
        self.play(FadeIn(bald_spot), FadeIn(bald_spot_text))
        self.wait(1)

        # Conclusion
        conclusion = Text("A continuous vector field on a 2-sphere\nmust have at least one zero vector.", font_size=28)
        conclusion.to_edge(DOWN)
        
        self.play(Write(conclusion))
        self.wait(2)

        # Final fade out
        self.play(
            *[FadeOut(mob) for mob in self.mobjects]
        )
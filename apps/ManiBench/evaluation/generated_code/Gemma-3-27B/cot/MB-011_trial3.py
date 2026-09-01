from manim import *

# Analysis:
# 1. Mobjects: Sphere, Arrows (vector field), Dot (bald spot), Text (labels)
# 2. Order: Sphere, Vector Field, Combing, Impossibility, Bald Spot Highlight
# 3. Transformations: Rotation, Vector Rotation, Scaling, Color Change
# 4. Timing: Synchronize vector rotation with sphere rotation, highlight after impossibility is shown.
# 5. Labels: "Hairy Ball Theorem", "Bald Spot"

class HairyBallTheorem(MovingCameraScene):
    def construct(self):
        # 1. Sphere
        sphere = Sphere(radius=2, resolution=(32, 32))
        sphere.set_shade_in_3d(True)
        self.play(Create(sphere), run_time=2)
        self.camera.frame.move_to(sphere.get_center() + OUT * 5)
        self.camera.frame.rotate(PI / 4, axis=UP)
        self.play(Rotate(sphere, angle=PI, axis=UP, run_time=4))

        # 2. Vector Field
        num_arrows = 100
        arrows = VGroup(*[Arrow(radius=0.1, color=BLUE, tip_length=0.15) for _ in range(num_arrows)])
        for arrow in arrows:
            arrow.set_angle(random.uniform(0, 2 * PI))
            arrow.set_phi(random.uniform(0, PI))
            arrow.move_to(sphere.get_surface_point(arrow.get_angle(), arrow.get_phi()))
            arrow.set_normal(sphere.get_normal_at_point(arrow.get_center()))

        self.play(Create(arrows), run_time=2)

        # 3 & 4. Combing and Impossibility
        self.play(Rotate(arrows, angle=PI, axis=UP, run_time=4))
        self.play(Rotate(arrows, angle=PI, axis=RIGHT, run_time=4))

        # Highlight Bald Spot
        bald_spot = Dot(color=RED, size=0.2)
        bald_spot.move_to(sphere.get_surface_point(0, 0))
        self.play(Create(bald_spot), run_time=1)

        label = Text("Bald Spot", color=RED)
        label.next_to(bald_spot, UP)
        self.play(Write(label), run_time=1)

        title = Text("Hairy Ball Theorem", color=YELLOW)
        title.to_edge(UP)
        self.play(Write(title), run_time=1)

        self.wait(2)
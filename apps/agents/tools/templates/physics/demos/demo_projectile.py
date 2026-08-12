"""Demo: projectile motion with flying particle (Manim defaults)."""

from manim import *

from manim_physics.compute import projectile_trajectory


class DemoProjectile(Scene):
    def construct(self):
        title = Text("Projectile motion", font_size=36)
        title.to_edge(UP)
        self.play(Write(title), run_time=0.6)

        traj = projectile_trajectory(v0=12.0, angle_deg=45.0)
        x_max = float(max(traj["x"])) + 1
        y_max = float(max(traj["y"])) + 1
        axes = Axes(
            x_range=[0, x_max, 2],
            y_range=[0, y_max, 1],
            x_length=8,
            y_length=4,
            tips=False,
            axis_config={"include_numbers": True, "font_size": 18},
        ).shift(DOWN * 0.4)
        labels = axes.get_axis_labels(MathTex("x"), MathTex("y"))
        self.play(Create(axes), FadeIn(labels), run_time=0.8)

        params = MathTex(r"v_0=12,\ \theta=45^\circ", font_size=32).next_to(title, DOWN)
        self.play(FadeIn(params), run_time=0.5)

        points = [axes.c2p(float(x), float(y)) for x, y in zip(traj["x"], traj["y"])]
        path = VMobject(color=BLUE, stroke_width=4)
        path.set_points_as_corners(points)

        ball = Dot(points[0], radius=0.12, color=YELLOW)
        self.play(GrowFromCenter(ball), run_time=0.4)
        self.play(MoveAlongPath(ball, path), Create(path), run_time=2.5, rate_func=linear)

        # velocity components at launch
        launch = points[0]
        v_arrow = Arrow(launch, axes.c2p(2.5, 2.5), buff=0, color=TEAL, stroke_width=4)
        v_lab = MathTex(r"\vec v_0", font_size=28, color=TEAL).next_to(v_arrow, UP, buff=0.05)
        self.play(GrowArrow(v_arrow), FadeIn(v_lab), run_time=0.7)
        self.play(Indicate(ball, color=YELLOW), run_time=0.6)
        self.wait(1.0)

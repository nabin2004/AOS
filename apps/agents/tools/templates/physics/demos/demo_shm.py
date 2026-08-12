"""Demo: SHM spring oscillation (Manim defaults)."""

from manim import *

from manim_physics.compute import shm_spring


class DemoSHM(Scene):
    def construct(self):
        title = Text("Simple harmonic motion", font_size=36)
        title.to_edge(UP)
        self.play(Write(title), run_time=0.6)

        data = shm_spring(A=1.0, omega=2.0, t_end=6.0, n=180)
        axes = Axes(
            x_range=[0, 6, 1],
            y_range=[-1.5, 1.5, 0.5],
            x_length=7.5,
            y_length=3.6,
            tips=False,
            axis_config={"include_numbers": True, "font_size": 18},
        ).shift(DOWN * 0.5 + LEFT * 0.5)
        self.play(Create(axes), run_time=0.7)

        eq = MathTex(r"x(t)=A\cos(\omega t)", font_size=34).next_to(title, DOWN)
        self.play(Write(eq), run_time=0.6)

        curve = axes.plot_line_graph(
            x_values=[float(t) for t in data["t"]],
            y_values=[float(x) for x in data["x"]],
            add_vertex_dots=False,
            line_color=BLUE,
        )["line_graph"]
        self.play(Create(curve), run_time=1.5)

        # animated mass on a spring schematic
        wall = Line(LEFT * 5.5 + UP * 2.2, LEFT * 5.5 + UP * 1.2, color=GREY_B, stroke_width=6)
        mass = Square(0.45, color=ORANGE, fill_opacity=0.8).move_to(LEFT * 3.2 + UP * 1.7)
        spring = always_redraw(
            lambda: Line(wall.get_center(), mass.get_left(), color=TEAL, stroke_width=3)
        )
        self.play(Create(wall), FadeIn(mass), Create(spring), run_time=0.6)

        # drive mass from sampled x (scaled)
        t_tracker = ValueTracker(0)

        def update_mass(m):
            # map time index
            t = t_tracker.get_value()
            idx = int((t / 6.0) * (len(data["x"]) - 1))
            idx = max(0, min(idx, len(data["x"]) - 1))
            x = float(data["x"][idx])
            m.move_to(LEFT * (3.2 - x) + UP * 1.7)

        mass.add_updater(update_mass)
        self.add(spring)
        self.play(t_tracker.animate.set_value(6.0), run_time=3.0, rate_func=linear)
        mass.clear_updaters()

        # energy flash
        i = len(data["t"]) // 4
        ke, pe = float(data["ke"][i]), float(data["pe"][i])
        energy = MathTex(
            rf"KE={ke:.2f},\ PE={pe:.2f}",
            font_size=28,
        ).to_edge(DOWN)
        self.play(FadeIn(energy), run_time=0.5)
        self.wait(1.0)

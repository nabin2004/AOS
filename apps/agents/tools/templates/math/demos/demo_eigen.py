"""Demo: eigenvalues / eigenvectors with animated vectors (Manim defaults)."""

from manim import *

from manim_math.compute import eig_2x2
from manim_viz import matrix_grid


class DemoEigen(Scene):
    def construct(self):
        title = Text("Eigenvalues of a 2×2 matrix", font_size=36)
        title.to_edge(UP)
        self.play(Write(title), run_time=0.7)

        A = [[2.0, 1.0], [1.0, 2.0]]
        w, v = eig_2x2(A)

        grid = matrix_grid(A, cell=0.7)
        a_lab = MathTex(r"A=", font_size=36).next_to(grid, LEFT)
        matrix_group = VGroup(a_lab, grid).arrange(RIGHT, buff=0.2).shift(LEFT * 3 + UP * 0.5)
        self.play(FadeIn(matrix_group), run_time=0.8)

        plane = NumberPlane(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=5,
            y_length=5,
            background_line_style={"stroke_opacity": 0.35},
        ).shift(RIGHT * 2.3 + DOWN * 0.2)
        self.play(Create(plane), run_time=0.8)

        colors = [YELLOW, TEAL]
        arrows = VGroup()
        for i in range(2):
            vx, vy = float(v[0, i]), float(v[1, i])
            # normalize length for display
            norm = (vx**2 + vy**2) ** 0.5 or 1.0
            scale = 1.8 / norm
            start = plane.c2p(0, 0)
            end = plane.c2p(vx * scale, vy * scale)
            arrow = Arrow(start, end, buff=0, color=colors[i], stroke_width=5)
            lab = MathTex(rf"v_{i+1}", font_size=28, color=colors[i]).next_to(end, UR, buff=0.05)
            self.play(GrowArrow(arrow), FadeIn(lab), run_time=0.7)
            arrows.add(VGroup(arrow, lab))

        eig_tex = MathTex(
            rf"\lambda_1={float(w[0]):.3g},\quad \lambda_2={float(w[1]):.3g}",
            font_size=34,
        ).to_edge(DOWN)
        self.play(Write(eig_tex), run_time=0.8)
        self.play(*[Indicate(a[0], color=a[0].get_color()) for a in arrows], run_time=0.8)
        self.wait(1.2)

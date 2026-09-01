from manim import *

class DeterminantVisualization(Scene):
    def construct(self):
        # 1. Unit parallelogram and label
        u = Vector([1, 0], color=BLUE, weight=0.8)
        v = Vector([0, 1], color=GREEN, weight=0.8)
        parallelogram = Polygon([0, 0], u, u + v, v, color=YELLOW, opacity=0.7)
        area_label = Tex("Original Area = 1", color=BLACK).next_to(parallelogram, UP)

        self.play(Create(u), Create(v), Create(parallelogram), Write(area_label))
        self.wait(1)

        # 2. 2x2 matrix
        matrix_a = MathTex("A = \\begin{pmatrix} 2 & 1 \\ 1 & 3 \\end{pmatrix}", color=BLACK).to_edge(UR)
        self.play(Write(matrix_a))
        self.wait(1)

        # 3. Transformation and grid deformation
        grid = VGroup(*[
            Line(x_start, x_end, color=GRAY, stroke_width=0.5)
            for x_start in np.linspace(-2, 2, 5)
            for x_end in [UP * 4]
        ], *[
            Line(y_start, y_end, color=GRAY, stroke_width=0.5)
            for y_start in np.linspace(-2, 2, 5)
            for y_end in [RIGHT * 4]
        ])

        def transform_point(point):
            matrix = np.array([[2, 1], [1, 3]])
            new_point = np.dot(matrix, point)
            return new_point

        def transform_mobject(mobject):
            transformed_points = [transform_point(point) for point in mobject.points]
            return Polygon(*transformed_points, color=mobject.color, opacity=mobject.opacity)

        transformed_parallelogram = transform_mobject(parallelogram)
        transformed_parallelogram.generate_target()
        transformed_parallelogram.target.shift(RIGHT * 2 + UP * 2)

        self.play(
            Transform(parallelogram, transformed_parallelogram.target),
            Transform(grid, transform_mobject(grid).target),
            run_time=3
        )
        self.wait(1)

        # 4. New area label
        det_a = np.linalg.det(np.array([[2, 1], [1, 3]]))
        new_area_label = Tex(f"New Area = |det(A)| = {det_a:.2f}", color=BLACK).next_to(transformed_parallelogram, UP)
        self.play(Write(new_area_label))

        # 5. Determinant value update
        det_value = always_updating(MathTex(f"det(A) = {det_a:.2f}", color=BLACK).to_edge(DL))
        self.play(Write(det_value))

        self.wait(2)
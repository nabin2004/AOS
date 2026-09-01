from manim import *

class DeterminantVisualization(Scene):
    def construct(self):
        # 1. Unit parallelogram and label
        u = Vector([1, 0], color=BLUE, weight=0.8)
        v = Vector([0, 1], color=GREEN, weight=0.8)
        parallelogram = Polygon([0, 0], [1, 0], [1, 1], [0, 1], color=YELLOW, opacity=0.5)
        area_label = Tex("Original Area = 1", color=BLACK)
        area_label.next_to(parallelogram, UP)

        self.play(Create(u), Create(v), Create(parallelogram), Write(area_label))
        self.wait(1)

        # 2. 2x2 matrix
        matrix_a = MathTex("A = \\begin{pmatrix} 2 & 1 \\ 1 & 3 \\end{pmatrix}", color=BLACK, weight=0.7)
        matrix_a.to_corner(UR)
        self.play(Write(matrix_a))
        self.wait(1)

        # 3. Transformation and grid deformation
        det_a = 5  # Calculate determinant
        grid = VGroup(*[
            Line(x * u[0] + v[0], x * u[1] + v[1], color=GRAY, stroke_width=0.5)
            for x in range(6)
        ])
        grid.surround(parallelogram)

        transformed_parallelogram = parallelogram.copy()
        transformed_u = u.copy()
        transformed_v = v.copy()

        matrix = [[2, 1], [1, 3]]
        transformed_u.become(transformed_u.copy().set_x(matrix[0][0] * u[0] + matrix[0][1] * v[0]).set_y(matrix[0][0] * u[1] + matrix[0][1] * v[1]))
        transformed_v.become(transformed_v.copy().set_x(matrix[1][0] * u[0] + matrix[1][1] * v[0]).set_y(matrix[1][0] * u[1] + matrix[1][1] * v[1]))
        transformed_parallelogram = Polygon([0, 0], transformed_u.get_end(), transformed_u.get_end() + transformed_v.get_end(), transformed_v.get_end(), color=YELLOW, opacity=0.5)

        transformed_grid = VGroup(*[
            Line(x * transformed_u[0] + transformed_v[0], x * transformed_u[1] + transformed_v[1], color=GRAY, stroke_width=0.5)
            for x in range(6)
        ])

        self.play(
            Transform(parallelogram, transformed_parallelogram),
            Transform(u, transformed_u),
            Transform(v, transformed_v),
            Transform(grid, transformed_grid)
        )
        self.wait(2)

        # 4. New area label
        new_area_label = Tex(f"New Area = |det(A)| = {det_a}", color=BLACK, weight=0.8)
        new_area_label.next_to(transformed_parallelogram, UP)
        self.play(Write(new_area_label))

        # 5. Determinant value display
        det_value = MathTex("det(A) = 5", color=BLACK, weight=0.8).to_corner(DL)
        self.play(Write(det_value))

        self.wait(3)
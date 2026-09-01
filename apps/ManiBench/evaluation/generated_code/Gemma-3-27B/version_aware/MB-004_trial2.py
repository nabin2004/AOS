from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # Coordinate Grid
        grid = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=10, y_length=10)
        grid.add_coordinate_labels()
        self.play(Create(grid))

        # Basis Vectors
        e1 = Arrow(ORIGIN, RIGHT, color=YELLOW)
        e2 = Arrow(ORIGIN, UP, color=GREEN)
        e1_label = Tex("e₁", color=YELLOW).next_to(e1, RIGHT)
        e2_label = Tex("e₂", color=GREEN).next_to(e2, UP)
        self.play(Create(e1), Create(e2), Write(e1_label), Write(e2_label))

        # Matrix A
        A = [[2, 1], [1, 2]]
        matrix_A = MathTex("A = \\begin{pmatrix} 2 & 1 \\\\ 1 & 2 \\end{pmatrix}").to_edge(UP)
        self.play(Write(matrix_A))

        # Eigenvalues and Eigenvectors
        eigenvalue1 = 3
        eigenvalue2 = 1
        eigenvector1 = [-1, 1]
        eigenvector2 = [1, 1]

        eigenvalue1_tex = MathTex("\\lambda_1 = 3").next_to(matrix_A, DOWN)
        eigenvalue2_tex = MathTex("\\lambda_2 = 1").next_to(eigenvalue1_tex, DOWN)
        eigenvector1_tex = MathTex("v_1 = \\begin{pmatrix} -1 \\\\ 1 \\end{pmatrix}").next_to(eigenvalue2_tex, DOWN)
        eigenvector2_tex = MathTex("v_2 = \\begin{pmatrix} 1 \\\\ 1 \\end{pmatrix}").next_to(eigenvector1_tex, DOWN)

        self.play(Write(eigenvalue1_tex), Write(eigenvalue2_tex), Write(eigenvector1_tex), Write(eigenvector2_tex))

        # Visualize Eigenvectors
        eigenvector1_arrow = Arrow(ORIGIN, eigenvector1, color=RED)
        eigenvector2_arrow = Arrow(ORIGIN, eigenvector2, color=BLUE)
        eigenvector1_label = Tex("v₁", color=RED).next_to(eigenvector1_arrow, RIGHT)
        eigenvector2_label = Tex("v₂", color=BLUE).next_to(eigenvector2_arrow, RIGHT)
        self.play(Create(eigenvector1_arrow), Write(eigenvector1_label), Create(eigenvector2_arrow), Write(eigenvector2_label))

        # Transformation
        def transform(point):
            x, y = point
            new_x = A[0][0] * x + A[0][1] * y
            new_y = A[1][0] * x + A[1][1] * y
            return new_x, new_y

        transformed_grid = grid.copy()
        for i in range(transformed_grid.num_points):
            point = transformed_grid.points[i]
            transformed_grid.points[i] = transform(point)

        transformed_e1 = Arrow(ORIGIN, [A[0][0], A[1][0]], color=YELLOW)
        transformed_e2 = Arrow(ORIGIN, [A[0][1], A[1][1]], color=GREEN)

        transformed_eigenvector1 = Arrow(ORIGIN, [eigenvalue1 * eigenvector1[0], eigenvalue1 * eigenvector1[1]], color=RED)
        transformed_eigenvector2 = Arrow(ORIGIN, [eigenvalue2 * eigenvector2[0], eigenvalue2 * eigenvector2[1]], color=BLUE)

        self.play(
            Transform(grid, transformed_grid),
            Transform(e1, transformed_e1),
            Transform(e2, transformed_e2),
            Transform(eigenvector1_arrow, transformed_eigenvector1),
            Transform(eigenvector2_arrow, transformed_eigenvector2),
            run_time=2
        )

        # Highlight Special Property
        special_text = Tex("Eigenvectors only change length!").to_edge(DOWN)
        self.play(Write(special_text))

        self.wait(2)
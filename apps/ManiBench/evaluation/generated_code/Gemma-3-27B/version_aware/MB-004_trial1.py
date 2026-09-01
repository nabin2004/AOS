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
        self.play(Create(e1), Create(e2))

        # Matrix A
        A = [[2, 1], [1, 2]]
        matrix_text = MathTex("A = \\begin{pmatrix} 2 & 1 \\\\ 1 & 2 \\end{pmatrix}")
        matrix_text.next_to(e2, UP)
        self.play(Write(matrix_text))

        # Eigenvalues and Eigenvectors
        eigenvalues = [3, 1]
        eigenvector1 = np.array([1, 1])
        eigenvector2 = np.array([-1, 1])

        lambda1_text = MathTex("\\lambda_1 = 3")
        lambda1_text.next_to(matrix_text, DOWN)
        lambda2_text = MathTex("\\lambda_2 = 1")
        lambda2_text.next_to(lambda1_text, DOWN)

        eigenvector1_arrow = Arrow(ORIGIN, eigenvector1, color=RED)
        eigenvector2_arrow = Arrow(ORIGIN, eigenvector2, color=BLUE)
        eigenvector1_arrow.set_stroke(width=2)
        eigenvector2_arrow.set_stroke(width=2)

        self.play(Write(lambda1_text), Write(lambda2_text))
        self.play(Create(eigenvector1_arrow), Create(eigenvector2_arrow))

        # Transformation
        def transform(point):
            x, y = point
            new_x = A[0][0] * x + A[0][1] * y
            new_y = A[1][0] * x + A[1][1] * y
            return np.array([new_x, new_y])

        transformed_grid = VGroup()
        for i in range(-5, 6):
            for j in range(-5, 6):
                point = np.array([i, j])
                transformed_point = transform(point)
                dot = Dot(transformed_point, color=WHITE, radius=0.05)
                transformed_grid.add(dot)

        self.play(
            Transform(grid, transformed_grid),
            Transform(e1, Arrow(ORIGIN, transform(RIGHT), color=YELLOW)),
            Transform(e2, Arrow(ORIGIN, transform(UP), color=GREEN)),
            run_time=2
        )

        # Highlight Eigenvectors
        transformed_eigenvector1 = transform(eigenvector1)
        transformed_eigenvector2 = transform(eigenvector2)

        transformed_eigenvector1_arrow = Arrow(ORIGIN, transformed_eigenvector1, color=RED)
        transformed_eigenvector2_arrow = Arrow(ORIGIN, transformed_eigenvector2, color=BLUE)
        transformed_eigenvector1_arrow.set_stroke(width=2)
        transformed_eigenvector2_arrow.set_stroke(width=2)

        self.play(
            ReplacementTransform(eigenvector1_arrow, transformed_eigenvector1_arrow),
            ReplacementTransform(eigenvector2_arrow, transformed_eigenvector2_arrow)
        )

        # Special Highlight
        special_text = Text("Eigenvectors are special!", color=PURPLE)
        special_text.to_edge(DOWN)
        self.play(Write(special_text))

        self.wait(2)
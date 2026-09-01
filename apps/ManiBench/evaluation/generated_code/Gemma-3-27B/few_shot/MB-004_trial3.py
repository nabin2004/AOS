from manim import *
import numpy as np

class EigenvectorTransformation(Scene):
    def construct(self):
        # Define matrix A
        A = np.array([[2, 1], [1, 2]])
        eigenvalues, eigenvectors = np.linalg.eig(A)
        lambda1, lambda2 = eigenvalues
        v1, v2 = eigenvectors.T

        # Coordinate grid
        grid = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=10, y_length=10)
        grid_lines = grid.get_lines()

        # Basis vectors
        e1 = Arrow(ORIGIN, RIGHT * 3, color=GREEN, stroke_width=2, tip_length=0.3)
        e2 = Arrow(ORIGIN, UP * 3, color=GREEN, stroke_width=2, tip_length=0.3)
        e1_label = MathTex("e_1").next_to(e1, RIGHT)
        e2_label = MathTex("e_2").next_to(e2, UP)

        # Eigenvectors
        eigenvector1 = Arrow(ORIGIN, v1 * 3, color=RED, stroke_width=2, tip_length=0.3)
        eigenvector2 = Arrow(ORIGIN, v2 * 3, color=BLUE, stroke_width=2, tip_length=0.3)
        lambda1_label = MathTex(f"\\lambda_1 = {lambda1:.2f}").next_to(eigenvector1, RIGHT)
        lambda2_label = MathTex(f"\\lambda_2 = {lambda2:.2f}").next_to(eigenvector2, RIGHT)

        # Random vector
        random_vector = Arrow(ORIGIN, [0.5, 1.5], color=YELLOW, stroke_width=2, tip_length=0.3)

        # Transformation function
        def transform_point(point):
            x, y = point
            new_x = A[0, 0] * x + A[0, 1] * y
            new_y = A[1, 0] * x + A[1, 1] * y
            return np.array([new_x, new_y])

        # Initial scene
        self.play(Create(grid_lines), Write(e1_label), Write(e2_label), Create(e1), Create(e2))
        self.play(Create(eigenvector1), Write(lambda1_label), Create(eigenvector2), Write(lambda2_label), Create(random_vector))
        self.wait(1)

        # Transformation
        transformed_grid = VGroup(*[grid_lines.copy() for _ in range(len(grid_lines))])
        for i, line in enumerate(transformed_grid):
            for point in line.points:
                new_point = transform_point(point)
                line.points[i] = new_point
        
        transformed_e1 = Arrow(ORIGIN, transform_point(e1.get_end()), color=GREEN, stroke_width=2, tip_length=0.3)
        transformed_e2 = Arrow(ORIGIN, transform_point(e2.get_end()), color=GREEN, stroke_width=2, tip_length=0.3)
        transformed_eigenvector1 = Arrow(ORIGIN, transform_point(eigenvector1.get_end()), color=RED, stroke_width=2, tip_length=0.3)
        transformed_eigenvector2 = Arrow(ORIGIN, transform_point(eigenvector2.get_end()), color=BLUE, stroke_width=2, tip_length=0.3)
        transformed_random_vector = Arrow(ORIGIN, transform_point(random_vector.get_end()), color=YELLOW, stroke_width=2, tip_length=0.3)

        self.play(Transform(grid_lines, transformed_grid),
                  Transform(e1, transformed_e1),
                  Transform(e2, transformed_e2),
                  Transform(eigenvector1, transformed_eigenvector1),
                  Transform(eigenvector2, transformed_eigenvector2),
                  Transform(random_vector, transformed_random_vector),
                  run_time=2)
        self.wait(1)

        # Highlight special property
        eigenvector_highlight = SurroundingRectangle(eigenvector1, color=GREEN, buff=0.2)
        eigenvector_highlight2 = SurroundingRectangle(eigenvector2, color=GREEN, buff=0.2)
        special_text = Text("Eigenvectors are special!", font_size=24, color=GREEN).to_edge(DOWN)

        self.play(Create(eigenvector_highlight), Create(eigenvector_highlight2), Write(special_text))
        self.wait(2)
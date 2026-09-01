from manim import *
import numpy as np

class EigenvectorTransformation(Scene):
    def construct(self):
        # Define the matrix A
        A = np.array([[2, 1], [1, 2]])
        eigenvalues, eigenvectors = np.linalg.eig(A)
        lambda1 = eigenvalues[0]
        lambda2 = eigenvalues[1]
        v1 = eigenvectors[:, 0]
        v2 = eigenvectors[:, 1]

        # Coordinate grid
        grid = NumberPlane(x_range=[-3, 3], y_range=[-3, 3], x_length=6, y_length=6)
        grid_lines = grid.get_lines()

        # Basis vectors
        e1 = Arrow(grid.coords_to_point(0, 0), grid.coords_to_point(1, 0), color=YELLOW, buff=0)
        e2 = Arrow(grid.coords_to_point(0, 0), grid.coords_to_point(0, 1), color=YELLOW, buff=0)
        e1_label = MathTex("e_1").next_to(e1, RIGHT)
        e2_label = MathTex("e_2").next_to(e2, UP)

        # Eigenvectors
        eigenvector1 = Arrow(grid.coords_to_point(0, 0), grid.coords_to_point(v1[0], v1[1]), color=RED, buff=0)
        eigenvector2 = Arrow(grid.coords_to_point(0, 0), grid.coords_to_point(v2[0], v2[1]), color=BLUE, buff=0)
        lambda1_label = MathTex("\\lambda_1 = " + str(round(lambda1, 2))).to_edge(UR)
        lambda2_label = MathTex("\\lambda_2 = " + str(round(lambda2, 2))).next_to(lambda1_label, DOWN)

        # Random vector
        random_vector = Arrow(grid.coords_to_point(0, 0), grid.coords_to_point(1.5, -0.5), color=GREEN, buff=0)

        # Transformation
        transformed_grid = grid.copy()
        transformed_grid.generate_target()
        for point in transformed_grid.get_points():
            x, y = point
            new_x, new_y = np.dot(A, [x, y])
            transformed_grid.target.put_point(transformed_grid.coords_to_point(x, y), (new_x, new_y))

        transformed_eigenvector1 = Arrow(grid.coords_to_point(0, 0), grid.coords_to_point(lambda1 * v1[0], lambda1 * v1[1]), color=RED, buff=0)
        transformed_eigenvector2 = Arrow(grid.coords_to_point(0, 0), grid.coords_to_point(lambda2 * v2[0], lambda2 * v2[1]), color=BLUE, buff=0)
        transformed_random_vector = Arrow(grid.coords_to_point(0, 0), grid.coords_to_point(np.dot(A, [1.5, -0.5])[0], np.dot(A, [1.5, -0.5])[1]), color=GREEN, buff=0)

        # Initial scene
        self.play(Create(grid_lines), Write(e1_label), Write(e2_label))
        self.play(Create(e1), Create(e2))
        self.play(Create(eigenvector1), Write(lambda1_label), Create(eigenvector2), Write(lambda2_label))
        self.play(Create(random_vector))
        self.wait(1)

        # Transformation
        self.play(Transform(transformed_grid, transformed_grid.target), run_time=2)
        self.play(Transform(random_vector, transformed_random_vector))
        self.play(Transform(eigenvector1, transformed_eigenvector1), Transform(eigenvector2, transformed_eigenvector2))
        self.wait(1)

        # Highlight special property
        special_text = Text("Eigenvectors are special!", font_size=24, color=YELLOW).to_edge(DOWN)
        self.play(Write(special_text))
        self.wait(2)
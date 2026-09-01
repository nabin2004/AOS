from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # 1. Coordinate Grid
        grid = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=10, y_length=10,
                           axis_config={"include_numbers": False},
                           grid_line_config={"color": GREY, "weight": 0.8})
        self.play(Create(grid))

        # 2. Basis Vectors
        e1 = Vector([1, 0], color=YELLOW, buff=0)
        e2 = Vector([0, 1], color=BLUE, buff=0)
        self.play(Create(e1), Create(e2))

        # 3. Define Matrix A and Eigenvectors
        A = [[2, 1], [1, 2]]
        eigenvalues = [3, 1]
        eigenvectors = [[1, 1], [-1, 1]]

        # 4. Eigenvectors Visualization
        eigenvector1 = Vector(eigenvectors[0], color=RED, buff=0)
        eigenvector2 = Vector(eigenvectors[1], color=GREEN, buff=0)
        self.play(Create(eigenvector1), Create(eigenvector2))

        # 5. Eigenvalue Labels
        lambda1_text = Tex(r"$\lambda_1 = 3$", color=RED).next_to(eigenvector1, UP + RIGHT)
        lambda2_text = Tex(r"$\lambda_2 = 1$", color=GREEN).next_to(eigenvector2, UP + LEFT)
        self.play(Write(lambda1_text), Write(lambda2_text))

        # 6. Transformation Animation
        def transform_point(point):
            x = point[0]
            y = point[1]
            new_x = A[0][0] * x + A[0][1] * y
            new_y = A[1][0] * x + A[1][1] * y
            return [new_x, new_y]

        transformed_grid = VGroup()
        for i in range(-5, 6):
            for j in range(-5, 6):
                point = [i, j]
                transformed_point = transform_point(point)
                dot = Dot(transformed_point, color=GREY, radius=0.05)
                transformed_grid.add(dot)

        transformed_e1 = Vector(transform_point(e1.get_end()), color=YELLOW, buff=0)
        transformed_e2 = Vector(transform_point(e2.get_end()), color=BLUE, buff=0)
        transformed_eigenvector1 = Vector(transform_point(eigenvector1.get_end()), color=RED, buff=0)
        transformed_eigenvector2 = Vector(transform_point(eigenvector2.get_end()), color=GREEN, buff=0)

        self.play(
            Transform(grid, transformed_grid),
            Transform(e1, transformed_e1),
            Transform(e2, transformed_e2),
            Transform(eigenvector1, transformed_eigenvector1),
            Transform(eigenvector2, transformed_eigenvector2),
            run_time=2
        )

        # 7. Highlight Eigenvector Property
        self.play(Indicate(eigenvector1), Indicate(eigenvector2))
        self.wait(1)
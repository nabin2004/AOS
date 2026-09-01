from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # 1. Coordinate Grid
        grid = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=10, y_length=10,
                           axis_config={"include_numbers": False},
                           background_color=WHITE)
        grid.add_coordinate_labels()
        self.play(Create(grid))

        # 2. Basis Vectors
        e1 = Arrow(ORIGIN, RIGHT, buff=0, color=YELLOW, stroke_width=2)
        e2 = Arrow(ORIGIN, UP, buff=0, color=GREEN, stroke_width=2)
        self.play(Create(e1), Create(e2))

        # 3. Define Matrix A and Eigenvectors
        A = [[2, 1], [1, 2]]
        eigenvalues = [3, 1]
        eigenvectors = [[1, 1], [1, -1]]

        # 4. Eigenvectors as Mobjects
        eigenvector1 = Arrow(ORIGIN, eigenvectors[0][0] * RIGHT + eigenvectors[0][1] * UP,
                             buff=0, color=RED, stroke_width=2)
        eigenvector2 = Arrow(ORIGIN, eigenvectors[1][0] * RIGHT + eigenvectors[1][1] * UP,
                             buff=0, color=BLUE, stroke_width=2)
        self.play(Create(eigenvector1), Create(eigenvector2))

        # 5. Eigenvalue Labels
        lambda1_text = Tex(r"$\lambda_1 = 3$", color=RED).next_to(eigenvector1.get_end(), RIGHT)
        lambda2_text = Tex(r"$\lambda_2 = 1$", color=BLUE).next_to(eigenvector2.get_end(), RIGHT)
        self.play(Write(lambda1_text), Write(lambda2_text))

        # 6. Transformation
        def transform_point(point):
            x, y = point
            new_x = A[0][0] * x + A[0][1] * y
            new_y = A[1][0] * x + A[1][1] * y
            return new_x, new_y

        def transform_mobject(mobject):
            if isinstance(mobject, Arrow):
                end = mobject.get_end()
                new_end = transform_point(end)
                mobject.put_end_on(new_end)
                return mobject
            else:
                return mobject

        # Apply transformation to grid lines
        grid_lines = grid.get_lines()
        transformed_grid_lines = VGroup(*[transform_mobject(line) for line in grid_lines])

        # Apply transformation to basis vectors
        transformed_e1 = transform_mobject(e1)
        transformed_e2 = transform_mobject(e2)

        # Apply transformation to eigenvectors
        transformed_eigenvector1 = transform_mobject(eigenvector1)
        transformed_eigenvector2 = transform_mobject(eigenvector2)

        # Animate the transformation
        self.play(
            Transform(grid, transformed_grid_lines),
            Transform(e1, transformed_e1),
            Transform(e2, transformed_e2),
            Transform(eigenvector1, transformed_eigenvector1),
            Transform(eigenvector2, transformed_eigenvector2),
            run_time=2
        )

        # 7. Highlight Eigenvector Property
        self.play(Indicate(eigenvector1), Indicate(eigenvector2))
        self.wait(1)
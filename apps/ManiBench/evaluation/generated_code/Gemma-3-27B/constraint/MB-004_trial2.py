from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # Define the matrix A
        A = [[3, 1], [0, 2]]

        # Define eigenvalues and eigenvectors
        eigenvalues = [3, 2]
        eigenvectors = [[1, 0], [0, 1]]

        # Create the coordinate grid
        grid = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=10, y_length=10,
                           grid_step=1, grid_color=GREY, grid_stroke_width=0.8)
        self.play(Create(grid))

        # Highlight basis vectors
        e1 = Arrow(ORIGIN, RIGHT * 3, color=RED, buff=0)
        e2 = Arrow(ORIGIN, UP * 3, color=BLUE, buff=0)
        self.play(Create(e1), Create(e2))

        # Display matrix A
        matrix_text = Tex(f"A = [[{A[0][0]}, {A[0][1]}], [{A[1][0]}, {A[1][1]}]]")
        matrix_text.to_corner(UL)
        self.play(Write(matrix_text))

        # Define a non-eigenvector
        non_eigenvector = Arrow(ORIGIN, [1, 1] * 2, color=GREEN)
        self.play(Create(non_eigenvector))

        # Create eigenvectors as arrows
        eigenvector1 = Arrow(ORIGIN, eigenvectors[0][0] * RIGHT * 3, color=RED)
        eigenvector2 = Arrow(ORIGIN, eigenvectors[1][1] * UP * 3, color=BLUE)

        # Display eigenvalue labels
        lambda1_text = Tex(f"λ₁ = {eigenvalues[0]}")
        lambda1_text.next_to(eigenvector1, UP)
        lambda2_text = Tex(f"λ₂ = {eigenvalues[1]}")
        lambda2_text.next_to(eigenvector2, UP)

        self.play(Create(eigenvector1), Create(eigenvector2), Write(lambda1_text), Write(lambda2_text))

        self.wait(1)

        # Apply the transformation
        def transform_point(point):
            x = point[0]
            y = point[1]
            new_x = A[0][0] * x + A[0][1] * y
            new_y = A[1][0] * x + A[1][1] * y
            return [new_x, new_y]

        transformed_grid = grid.copy()
        transformed_e1 = Arrow(ORIGIN, transform_point(RIGHT * 3), color=RED)
        transformed_e2 = Arrow(ORIGIN, transform_point(UP * 3), color=BLUE)
        transformed_non_eigenvector = Arrow(ORIGIN, transform_point([1, 1] * 2), color=GREEN)
        transformed_eigenvector1 = Arrow(ORIGIN, transform_point(eigenvectors[0][0] * RIGHT * 3), color=RED)
        transformed_eigenvector2 = Arrow(ORIGIN, transform_point(eigenvectors[1][1] * UP * 3), color=BLUE)

        self.play(
            Transform(grid, transformed_grid),
            Transform(e1, transformed_e1),
            Transform(e2, transformed_e2),
            Transform(non_eigenvector, transformed_non_eigenvector),
            Transform(eigenvector1, transformed_eigenvector1),
            Transform(eigenvector2, transformed_eigenvector2),
            run_time=2
        )

        self.wait(2)

        # Highlight that eigenvectors remain on the same line
        eigenvector_highlight_text = Tex("Eigenvectors remain collinear!")
        eigenvector_highlight_text.to_corner(DR)
        self.play(Write(eigenvector_highlight_text))

        self.wait(1)
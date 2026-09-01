from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # Define the matrix A
        A = [[2, 1], [1, 2]]
        eigenvalues, eigenvectors = np.linalg.eig(A)
        lambda1 = eigenvalues[0]
        lambda2 = eigenvalues[1]
        v1 = eigenvectors[:, 0]
        v2 = eigenvectors[:, 1]

        # Create the coordinate grid
        grid = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=10, y_length=10)
        grid.add_coordinate_labels()

        # Highlight basis vectors
        e1 = Arrow(ORIGIN, RIGHT * 5, buff=0, color=YELLOW)
        e2 = Arrow(ORIGIN, UP * 5, buff=0, color=GREEN)
        e1_label = Tex("e₁").next_to(e1, RIGHT)
        e2_label = Tex("e₂").next_to(e2, UP)

        # Create eigenvectors as arrows
        eigenvector1 = Arrow(ORIGIN, v1 * 5, buff=0, color=RED)
        eigenvector2 = Arrow(ORIGIN, v2 * 5, buff=0, color=BLUE)
        lambda1_text = Tex(f"λ₁ = {lambda1:.2f}").next_to(eigenvector1, RIGHT)
        lambda2_text = Tex(f"λ₂ = {lambda2:.2f}").next_to(eigenvector2, RIGHT)

        # Group elements for easier manipulation
        grid_group = VGroup(grid, e1, e2, e1_label, e2_label)
        eigenvector_group = VGroup(eigenvector1, eigenvector2, lambda1_text, lambda2_text)

        # Show initial state
        self.play(Create(grid_group))
        self.play(Create(eigenvector_group))
        self.wait(1)

        # Apply the transformation
        matrix_transformation = TransformationMatrix(A)
        transformed_grid = grid_group.copy().transform(matrix_transformation)
        transformed_eigenvector1 = eigenvector1.copy().transform(matrix_transformation)
        transformed_eigenvector2 = eigenvector2.copy().transform(matrix_transformation)

        self.play(Transform(grid_group, transformed_grid),
                  Transform(eigenvector1, transformed_eigenvector1),
                  Transform(eigenvector2, transformed_eigenvector2),
                  run_time=2)

        self.wait(1)

        # Highlight that eigenvectors are special
        eigenvector1_line = Line(ORIGIN, v1 * 5, color=RED)
        eigenvector2_line = Line(ORIGIN, v2 * 5, color=BLUE)
        transformed_eigenvector1_line = Line(ORIGIN, transformed_eigenvector1.get_end(), color=RED)
        transformed_eigenvector2_line = Line(ORIGIN, transformed_eigenvector2.get_end(), color=BLUE)

        special_text = Tex("Eigenvectors are special!").to_edge(UP)

        self.play(
            FadeOut(eigenvector1, eigenvector2, lambda1_text, lambda2_text),
            Create(eigenvector1_line),
            Create(eigenvector2_line),
            Create(transformed_eigenvector1_line),
            Create(transformed_eigenvector2_line),
            Write(special_text)
        )
        self.wait(2)
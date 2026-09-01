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
        
        # Animate the transformation
        self.play(
            ApplyPoint(matrix_transformation, grid_group),
            ApplyPoint(matrix_transformation, eigenvector_group),
            run_time=2
        )
        self.wait(1)

        # Highlight that eigenvectors are special
        eigenvector1_transformed = Arrow(ORIGIN, matrix_transformation.get_vector(v1) * 5, buff=0, color=RED)
        eigenvector2_transformed = Arrow(ORIGIN, matrix_transformation.get_vector(v2) * 5, buff=0, color=BLUE)
        
        self.play(
            Transform(eigenvector1, eigenvector1_transformed),
            Transform(eigenvector2, eigenvector2_transformed),
            Write(Tex("Eigenvectors only change length!").to_edge(UP))
        )
        self.wait(2)
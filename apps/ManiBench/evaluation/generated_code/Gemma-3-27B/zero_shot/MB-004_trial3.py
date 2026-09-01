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
        grid_color = GREY_B

        # Highlight basis vectors
        e1 = Arrow(ORIGIN, RIGHT * 5, buff=0, color=RED)
        e2 = Arrow(ORIGIN, UP * 5, buff=0, color=BLUE)
        e1_label = Tex("e₁").next_to(e1, RIGHT)
        e2_label = Tex("e₂").next_to(e2, UP)

        # Create eigenvectors as arrows
        eigenvector1 = Arrow(ORIGIN, v1 * 5, buff=0, color=RED)
        eigenvector2 = Arrow(ORIGIN, v2 * 5, buff=0, color=BLUE)
        lambda1_text = Tex(f"λ₁ = {lambda1:.2f}").next_to(eigenvector1, RIGHT)
        lambda2_text = Tex(f"λ₂ = {lambda2:.2f}").next_to(eigenvector2, RIGHT)

        # Create a sample vector
        sample_vector = Arrow(ORIGIN, [3, 1], buff=0, color=YELLOW)

        # Group elements for easier manipulation
        grid_group = VGroup(grid, e1, e2, e1_label, e2_label)
        eigenvector_group = VGroup(eigenvector1, eigenvector2, lambda1_text, lambda2_text)
        vector_group = VGroup(sample_vector)

        # Show initial state
        self.play(Create(grid_group))
        self.play(Create(eigenvector_group))
        self.play(Create(vector_group))
        self.wait(1)

        # Apply the transformation
        matrix_transformation = self.matrix_to_transformation(A)
        self.play(Transform(grid_group, grid_group.apply_matrix(matrix_transformation)),
                  Transform(eigenvector_group, eigenvector_group.apply_matrix(matrix_transformation)),
                  Transform(vector_group, vector_group.apply_matrix(matrix_transformation)),
                  run_time=2)

        self.wait(1)

        # Highlight eigenvectors as special
        eigenvector1_highlight = SurroundingRectangle(eigenvector1, color=GREEN, buff=0.2)
        eigenvector2_highlight = SurroundingRectangle(eigenvector2, color=GREEN, buff=0.2)
        special_text = Tex("Eigenvectors are special!").to_edge(UP)

        self.play(Create(eigenvector1_highlight), Create(eigenvector2_highlight), Write(special_text))
        self.wait(2)

        self.play(FadeOut(grid_group, eigenvector_group, vector_group, eigenvector1_highlight, eigenvector2_highlight, special_text))

    def matrix_to_transformation(self, matrix):
        return np.array([[matrix[0][0], matrix[0][1], 0],
                         [matrix[1][0], matrix[1][1], 0],
                         [0, 0, 1]])
from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # Define the matrix A
        A = [[2, 1], [1, 2]]
        
        # Calculate eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eig(A)
        lambda1 = eigenvalues[0]
        lambda2 = eigenvalues[1]
        v1 = eigenvectors[:, 0]
        v2 = eigenvectors[:, 1]

        # Create coordinate grid
        grid = NumberPlane(x_range=[-5, 5], y_range=[-5, 5], x_length=10, y_length=10)
        grid.add_coordinate_labels()
        self.play(Create(grid))

        # Highlight basis vectors
        e1 = Arrow(ORIGIN, RIGHT * 3, buff=0, color=YELLOW)
        e2 = Arrow(ORIGIN, UP * 3, buff=0, color=GREEN)
        e1_label = Tex("e₁").next_to(e1, RIGHT)
        e2_label = Tex("e₂").next_to(e2, UP)
        self.play(Create(e1), Create(e2), Write(e1_label), Write(e2_label))

        # Define eigenvectors as arrows
        eigenvector1 = Arrow(ORIGIN, v1 * 3, buff=0, color=RED)
        eigenvector2 = Arrow(ORIGIN, v2 * 3, buff=0, color=BLUE)
        lambda1_text = Tex(f"λ₁ = {lambda1:.2f}").next_to(eigenvector1, RIGHT)
        lambda2_text = Tex(f"λ₂ = {lambda2:.2f}").next_to(eigenvector2, RIGHT)
        v1_label = Tex("v₁").next_to(eigenvector1, DOWN)
        v2_label = Tex("v₂").next_to(eigenvector2, DOWN)
        self.play(Create(eigenvector1), Create(eigenvector2), Write(lambda1_text), Write(lambda2_text), Write(v1_label), Write(v2_label))

        # Create a vector that is not an eigenvector
        random_vector = np.array([1.5, 0.5])
        random_arrow = Arrow(ORIGIN, random_vector * 3, buff=0, color=GRAY)
        random_label = Tex("general vector").next_to(random_arrow, DOWN)
        self.play(Create(random_arrow), Write(random_label))

        # Apply the transformation
        def transform_point(point):
            x, y = point
            new_x = A[0][0] * x + A[0][1] * y
            new_y = A[1][0] * x + A[1][1] * y
            return np.array([new_x, new_y])

        transformed_grid = VGroup()
        for i in range(-5, 6):
            line = Line(start=grid.c2p(i, -5), end=grid.c2p(i, 5), color=WHITE)
            transformed_line = Line(start=transform_point(grid.c2p(i, -5)), end=transform_point(grid.c2p(i, 5)), color=WHITE)
            transformed_grid.add(transformed_line)

        for j in range(-5, 6):
            line = Line(start=grid.c2p(-5, j), end=grid.c2p(5, j), color=WHITE)
            transformed_line = Line(start=transform_point(grid.c2p(-5, j)), end=transform_point(grid.c2p(5, j)), color=WHITE)
            transformed_grid.add(transformed_line)
        
        transformed_eigenvector1 = Arrow(ORIGIN, transform_point(v1) * 3, buff=0, color=RED)
        transformed_eigenvector2 = Arrow(ORIGIN, transform_point(v2) * 3, buff=0, color=BLUE)
        transformed_random_arrow = Arrow(ORIGIN, transform_point(random_vector) * 3, buff=0, color=GRAY)

        self.play(
            Transform(grid, transformed_grid),
            Transform(eigenvector1, transformed_eigenvector1),
            Transform(eigenvector2, transformed_eigenvector2),
            Transform(random_arrow, transformed_random_arrow),
            run_time=2
        )

        # Highlight that eigenvectors are special
        eigenvector_text = Tex("Eigenvectors are special!").to_edge(UP)
        self.play(Write(eigenvector_text))
        self.wait(2)
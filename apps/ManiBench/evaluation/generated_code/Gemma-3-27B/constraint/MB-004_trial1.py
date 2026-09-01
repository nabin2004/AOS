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
                           grid_step=1, grid_color=GREY, grid_stroke_width=0.8, critical=True)
        self.play(Create(grid))

        # Highlight basis vectors
        e1 = Arrow(ORIGIN, RIGHT * 5, buff=0, color=RED, stroke_width=2)
        e2 = Arrow(ORIGIN, UP * 5, buff=0, color=BLUE, stroke_width=2)
        e1_label = Tex("e₁", color=RED).next_to(e1, RIGHT)
        e2_label = Tex("e₂", color=BLUE).next_to(e2, UP)
        self.play(Create(e1), Create(e2), Write(e1_label), Write(e2_label))
        self.wait(1)

        # Define a non-eigenvector
        v = Arrow(ORIGIN, [2, 3], buff=0, color=GREEN, stroke_width=2)
        v_label = Tex("v", color=GREEN).next_to(v, RIGHT)
        self.play(Create(v), Write(v_label))
        self.wait(0.5)

        # Define eigenvectors as arrows
        eigenvector1 = Arrow(ORIGIN, eigenvectors[0][0] * RIGHT * 5, buff=0, color=RED, stroke_width=2)
        eigenvector2 = Arrow(ORIGIN, eigenvectors[1][1] * UP * 5, buff=0, color=BLUE, stroke_width=2)
        eigenvalue1_text = Tex(f"λ₁ = {eigenvalues[0]}", color=RED).next_to(eigenvector1, RIGHT)
        eigenvalue2_text = Tex(f"λ₂ = {eigenvalues[1]}", color=BLUE).next_to(eigenvector2, UP)
        self.play(Create(eigenvector1), Create(eigenvector2), Write(eigenvalue1_text), Write(eigenvalue2_text))
        self.wait(1)

        # Display matrix A
        matrix_text = Tex(f"A = \\begin{{bmatrix}} {A[0][0]} & {A[0][1]} \\\\ {A[1][0]} & {A[1][1]} \\end{{bmatrix}}").to_edge(UP)
        self.play(Write(matrix_text))
        self.wait(0.5)

        # Apply the transformation
        def transform_point(point):
            x, y = point
            new_x = A[0][0] * x + A[0][1] * y
            new_y = A[1][0] * x + A[1][1] * y
            return [new_x, new_y]

        transformed_grid = grid.copy()
        transformed_e1 = Arrow(ORIGIN, transform_point(RIGHT * 5), buff=0, color=RED, stroke_width=2)
        transformed_e2 = Arrow(ORIGIN, transform_point(UP * 5), buff=0, color=BLUE, stroke_width=2)
        transformed_v = Arrow(ORIGIN, transform_point([2, 3]), buff=0, color=GREEN, stroke_width=2)
        transformed_eigenvector1 = Arrow(ORIGIN, transform_point(eigenvectors[0][0] * RIGHT * 5), buff=0, color=RED, stroke_width=2)
        transformed_eigenvector2 = Arrow(ORIGIN, transform_point(eigenvectors[1][1] * UP * 5), buff=0, color=BLUE, stroke_width=2)

        self.play(
            Transform(transformed_grid, transformed_grid),
            Transform(transformed_e1, transformed_e1),
            Transform(transformed_e2, transformed_e2),
            Transform(transformed_v, transformed_v),
            Transform(transformed_eigenvector1, transformed_eigenvector1),
            Transform(transformed_eigenvector2, transformed_eigenvector2),
            run_time=2
        )
        self.wait(2)

        # Highlight that eigenvectors remain on the same line
        eigenvector_highlight_text = Tex("Eigenvectors remain collinear!", color=YELLOW).to_edge(DOWN)
        self.play(Write(eigenvector_highlight_text))
        self.wait(2)

        self.play(FadeOut(grid, transformed_grid, e1, e2, e1_label, e2_label, v, v_label, eigenvector1, eigenvector2, eigenvalue1_text, eigenvalue2_text, transformed_e1, transformed_e2, transformed_v, transformed_eigenvector1, transformed_eigenvector2, matrix_text, eigenvector_highlight_text))
        self.wait()
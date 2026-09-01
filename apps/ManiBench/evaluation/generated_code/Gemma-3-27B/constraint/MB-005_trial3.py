from manim import *
import numpy as np

class DeterminantVisualization(Scene):
    def construct(self):
        # Define basis vectors
        u = np.array([1, 0])
        v = np.array([0, 1])

        # Create parallelogram
        parallelogram = Polygon(np.array([0, 0]), u, u + v, v)
        parallelogram.set_fill(BLUE, opacity=0.7)

        # Original area label
        original_area_text = Tex("Original Area = 1").scale(0.7)
        original_area_text.next_to(parallelogram, UP)

        # Matrix A
        matrix_a = np.array([[2, 1], [1, 3]])
        matrix_text = Tex(f"A = \begin{bmatrix} {matrix_a[0, 0]} & {matrix_a[0, 1]} \\\\ {matrix_a[1, 0]} & {matrix_a[1, 1]} \\end{bmatrix}").scale(0.7)
        matrix_text.next_to(original_area_text, RIGHT)

        # Determinant value
        det_a = np.linalg.det(matrix_a)
        det_text = Tex(f"det(A) = {det_a:.2f}").scale(0.7)
        det_text.next_to(matrix_text, RIGHT)

        # Initial state
        self.play(Create(parallelogram), Write(original_area_text), Write(matrix_text), Write(det_text))
        self.wait(2)

        # Transformation
        transformed_parallelogram = parallelogram.copy()
        transformed_parallelogram.apply_matrix(matrix_a)

        # New area label
        new_area_text = Tex(f"New Area = |det(A)| = {abs(det_a):.2f}").scale(0.7)
        new_area_text.next_to(parallelogram, DOWN)

        # Animate transformation and area update
        self.play(
            transformed_parallelogram.animate.apply_matrix(matrix_a),
            original_area_text.animate.to_edge(UP),
            det_text.animate.set_value(f"det(A) = {abs(det_a):.2f}")
        )
        self.play(Write(new_area_text))
        self.wait(2)
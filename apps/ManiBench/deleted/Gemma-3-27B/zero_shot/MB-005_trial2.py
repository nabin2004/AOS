from manim import *

class DeterminantVisualization(Scene):
    def construct(self):
        # Define the basis vectors
        u = np.array([1, 0])
        v = np.array([0, 1])

        # Create the original parallelogram
        parallelogram = Polygon(
            [0, 0], u, u + v, v
        ).set_fill(BLUE, opacity=0.5)
        parallelogram.set_label("Original Area = 1", font_size=24)

        # Define the matrix A
        A = np.array([[2, 1], [1, 3]])

        # Create the matrix text
        matrix_text = Tex(r"A = \begin{bmatrix} 2 & 1 \\ 1 & 3 \end{bmatrix}")

        # Calculate the determinant
        det_A = np.linalg.det(A)

        # Create the determinant text
        det_text = Tex(r"|det(A)| = ", "%.2f" % det_A).scale(0.75)

        # Group the original elements
        original_group = VGroup(parallelogram, matrix_text, det_text)
        original_group.arrange(DOWN)

        # Animate the transformation
        transformed_parallelogram = parallelogram.copy()
        transformed_parallelogram.apply_matrix(A)

        # Update the determinant text
        new_det_text = Tex(r"New Area = ", "%.2f" % abs(det_A)).scale(0.75)

        # Group the transformed elements
        transformed_group = VGroup(transformed_parallelogram, matrix_text, new_det_text)
        transformed_group.arrange(DOWN)

        # Show the original parallelogram
        self.play(Create(parallelogram))
        self.play(Write(matrix_text))
        self.play(Write(det_text))
        self.wait(2)

        # Animate the transformation
        self.play(
            Transform(parallelogram, transformed_parallelogram),
            Transform(det_text, new_det_text)
        )
        self.wait(2)
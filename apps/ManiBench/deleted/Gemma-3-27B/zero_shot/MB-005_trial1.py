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

        # Display the matrix A
        matrix_text = Tex(f"A = \begin{bmatrix} {A[0, 0]} & {A[0, 1]} \\ {A[1, 0]} & {A[1, 1]} \end{bmatrix}")
        matrix_text.to_edge(UP)

        # Calculate the determinant
        det_A = np.linalg.det(A)
        det_text = Tex(f"det(A) = {det_A:.2f}")
        det_text.next_to(matrix_text, DOWN)

        # Create the transformed parallelogram
        transformed_parallelogram = Polygon(
            [0, 0], A @ u, A @ u + A @ v, A @ v
        ).set_fill(RED, opacity=0.5)
        transformed_parallelogram.set_label(f"New Area = |{det_A:.2f}|", font_size=24)

        # Initial state
        self.play(Create(parallelogram), Write(matrix_text), Write(det_text))
        self.wait(2)

        # Animate the transformation
        self.play(
            Transform(parallelogram, transformed_parallelogram),
            UpdateFromFunc(
                det_text,
                lambda t: Tex(f"det(A) = {np.linalg.det(A):.2f}")
            )
        )
        self.wait(3)
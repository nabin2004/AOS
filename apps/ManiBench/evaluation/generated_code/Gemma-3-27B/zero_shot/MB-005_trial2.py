from manim import *

class DeterminantVisualization(Scene):
    def construct(self):
        # Define the matrix A
        A = [[2, 1], [1, 3]]
        det_A = np.linalg.det(A)

        # Define the basis vectors
        u = np.array([1, 0])
        v = np.array(0, 1)

        # Create the original parallelogram
        parallelogram = Polygon(
            [0, 0],
            u + v,
            u,
            v
        ).set_fill(BLUE, opacity=0.5)

        # Label the original area
        original_area_label = Tex("Original Area = 1").next_to(parallelogram, UP)

        # Display the matrix A
        matrix_label = Tex(f"A = \begin{bmatrix} {A[0][0]} & {A[0][1]} \\ {A[1][0]} & {A[1][1]} \\ \end{bmatrix}").to_edge(UR)

        # Create the transformed parallelogram
        transformed_parallelogram = VGroup()
        transformed_u = A[0][0] * u + A[0][1] * v
        transformed_v = A[1][0] * u + A[1][1] * v
        transformed_parallelogram = Polygon(
            [0, 0],
            transformed_u + transformed_v,
            transformed_u,
            transformed_v
        ).set_fill(GREEN, opacity=0.5)

        # Label the new area
        new_area_label = Tex("New Area = |det(A)|").next_to(transformed_parallelogram, UP)

        # Create a text object to display the determinant value
        det_label = Tex(f"det(A) = {det_A:.2f}").to_edge(DL)

        # Animate the transformation
        self.play(Create(parallelogram), Write(original_area_label), Write(matrix_label))
        self.wait(1)

        self.play(
            Transform(parallelogram, transformed_parallelogram),
            Transform(original_area_label, new_area_label),
            UpdateFromFunc(lambda mobj, dt: mobj.set_text(f"det(A) = {det_A:.2f}"), det_label)
        )
        self.wait(2)
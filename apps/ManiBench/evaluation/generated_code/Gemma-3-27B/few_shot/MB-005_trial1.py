from manim import *
import numpy as np

class DeterminantVisualization(Scene):
    def construct(self):
        # Define the matrix A
        A = np.array([[1.5, 0.5], [0.2, 1.2]])
        det_A = np.linalg.det(A)

        # Basis vectors
        u = np.array([1, 0])
        v = np.array([0, 1])

        # Create parallelogram
        parallelogram = Polygon(
            [0, 0],
            u,
            u + v,
            v,
            color=BLUE,
            fill_opacity=0.5
        )
        area_label = Text("Original Area = 1", font_size=24).to_edge(UP)

        # Matrix display
        matrix_label = MathTex(
            "A = \\begin{bmatrix} " + str(A[0, 0]) + " & " + str(A[0, 1]) + "\\\\ " + str(A[1, 0]) + " & " + str(A[1, 1]) + " \\end{bmatrix}",
            font_size=24
        ).to_edge(UR)

        det_label = MathTex("|det(A)| = ", str(round(det_A, 2))).next_to(matrix_label, DOWN)

        # Apply transformation
        transformed_parallelogram = VGroup()
        for point in parallelogram.points:
            transformed_point = A @ point
            transformed_parallelogram.add(Dot(transformed_point, color=RED))

        # Animate transformation
        self.play(Create(parallelogram), Write(area_label), Write(matrix_label), Write(det_label))
        self.wait(1)

        self.play(
            Transform(parallelogram, transformed_parallelogram),
            UpdateFromFunc(
                det_label,
                lambda l: MathTex("|det(A)| = ", str(round(det_A, 2)))
            ),
            run_time=3
        )
        self.wait(2)

        # Replace dots with a polygon
        transformed_polygon = Polygon(*[transformed_parallelogram[i].get_center() for i in range(len(transformed_parallelogram))], color=RED, fill_opacity=0.5)
        self.play(
            FadeTransform(transformed_parallelogram, transformed_polygon)
        )

        self.wait(1)
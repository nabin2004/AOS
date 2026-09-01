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

        # Labels
        original_area_label = Text("Original Area = 1", font_size=24).to_edge(UP)
        new_area_label = Text("New Area = |det(A)|", font_size=24).to_edge(UP)
        matrix_label = Tex(r"A = \begin{bmatrix} " + str(A[0, 0]) + " & " + str(A[0, 1]) + r" \\ " + str(A[1, 0]) + " & " + str(A[1, 1]) + r" \end{bmatrix}").to_edge(DOWN)
        det_value_label = Tex(r"\det(A) = ").next_to(matrix_label, UP)
        det_value_text = Tex(str(round(det_A, 2))).next_to(det_value_label, RIGHT)

        # Apply transformation
        def transform_point(point):
            return A @ point

        def transform_parallelogram(parallelogram_obj):
            transformed_points = [transform_point(point) for point in parallelogram_obj.points]
            return Polygon(*transformed_points, color=RED, fill_opacity=0.5)

        transformed_parallelogram = transform_parallelogram(parallelogram)

        # Animation
        self.play(Create(parallelogram), Write(original_area_label), Write(matrix_label), Write(det_value_label), Write(det_value_text))
        self.wait(1)

        self.play(
            Transform(parallelogram, transformed_parallelogram),
            FadeOut(original_area_label),
            Write(new_area_label),
            UpdateFromFunc(det_value_text, lambda x: Tex(str(round(det_A, 2))))
        )
        self.wait(2)
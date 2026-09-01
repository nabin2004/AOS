from manim import *
import numpy as np

class DeterminantVisualization(LinearTransformationScene):
    def __init__(self, matrix, **kwargs):
        super().__init__(**kwargs)
        self.matrix = np.array(matrix)
        self.det_value = self.matrix[0, 0] * self.matrix[1, 1] - self.matrix[0, 1] * self.matrix[1, 0]
        self.det_text = None

    def construct(self):
        # Define basis vectors
        u = Vector([1, 0], color=BLUE)
        v = Vector([0, 1], color=GREEN)

        # Create parallelogram
        parallelogram = Polygon(
            ORIGIN, u, u + v, v, color=YELLOW, fill_opacity=0.5
        )
        parallelogram_group = VGroup(u, v, parallelogram)

        # Initial area label
        area_label = Tex("Original Area = 1", color=BLACK).next_to(parallelogram, UP)

        # Matrix display
        matrix_label = MathTex(
            "A = \\begin{bmatrix} " + str(self.matrix[0, 0]) + " & " + str(self.matrix[0, 1]) + "\\\\ " + str(self.matrix[1, 0]) + " & " + str(self.matrix[1, 1]) + " \\end{bmatrix}",
            color=BLACK
        ).to_edge(UR)

        # Determinant display
        self.det_text = MathTex(
            "New Area = |" + str(round(self.det_value, 2)) + "|",
            color=BLACK
        ).next_to(area_label, DOWN)

        self.play(Create(u), Create(v), Create(parallelogram), Write(area_label), Write(matrix_label))
        self.wait(1)

        # Apply transformation
        transformed_parallelogram = self.transform(parallelogram_group, self.matrix)
        self.play(
            Transform(parallelogram_group, transformed_parallelogram),
            Transform(area_label, self.det_text)
        )
        self.wait(2)
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
            ORIGIN, u, u + v, v, color=YELLOW, opacity=0.5
        )
        parallelogram_group = VGroup(u, v, parallelogram)

        # Initial area label
        area_label = Tex("Original Area = 1", color=WHITE)
        area_label.to_corner(UP + LEFT)

        # Matrix display
        matrix_label = Tex(
            f"Matrix A = \n\\begin{{bmatrix}} {self.matrix[0, 0]} & {self.matrix[0, 1]} \\\\ {self.matrix[1, 0]} & {self.matrix[1, 1]} \\end{{bmatrix}}",
            color=WHITE
        )
        matrix_label.to_corner(UP + RIGHT)

        # Determinant display
        self.det_text = Tex(f"New Area = {self.det_value}", color=WHITE)
        self.det_text.to_corner(DOWN + LEFT)

        self.play(Create(u), Create(v), Create(parallelogram), Write(area_label), Write(matrix_label), Write(self.det_text))

        # Apply transformation
        self.play(
            Transform(u, self.matrix @ np.array([1, 0])),
            Transform(v, self.matrix @ np.array([0, 1])),
            Transform(parallelogram, self.matrix @ np.array([[1, 0], [0, 1]])),
            Update(self.det_text, lambda m: m.set_text(f"New Area = {abs(self.det_value)}"))
        )

        self.wait(2)
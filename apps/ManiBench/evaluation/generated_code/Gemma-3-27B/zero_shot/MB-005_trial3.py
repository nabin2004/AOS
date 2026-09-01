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
            u + [0, 0],
            u + v + [0, 0],
            v + [0, 0],
            color=BLUE,
            fill_opacity=0.5
        )
        parallelogram.set_label("Original Area = 1", font_size=24)

        # Create the matrix transformation
        def transform_point(point):
            return A @ point

        # Animate the transformation
        def update_parallelogram(mob, alpha):
            new_parallelogram = Polygon(
                transform_point([0, 0]),
                transform_point(u) + [0, 0],
                transform_point(u + v) + [0, 0],
                transform_point(v) + [0, 0],
                color=BLUE,
                fill_opacity=0.5
            )
            mob.become(new_parallelogram)
            mob.set_label(f"New Area = {abs(det_A):.2f}", font_size=24)
            return mob

        # Create the matrix text
        matrix_text = Tex(f"A = \\begin{{pmatrix}} {A[0][0]} & {A[0][1]} \\\\ {A[1][0]} & {A[1][1]} \\end{{pmatrix}}}")
        matrix_text.to_edge(UP)

        # Create the determinant text
        det_text = Tex(f"det(A) = {det_A:.2f}")
        det_text.next_to(matrix_text, DOWN)

        # Animate the determinant value
        def update_det_text(mob, alpha):
            new_det = np.linalg.det(A)
            mob.set_text(f"det(A) = {new_det:.2f}")
            return mob

        # Play the animation
        self.play(Create(parallelogram), Write(matrix_text), Write(det_text))
        self.play(Transform(parallelogram, update_parallelogram),
                  Update(det_text, update_det_text))
        self.wait(2)
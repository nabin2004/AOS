from manim import *
import numpy as np


class UpdateDeterminant(Animation):
    """
    A custom animation to update a DecimalNumber mobject with the determinant
    of a matrix as it's being interpolated during a transformation.
    """
    def __init__(self, decimal_number: DecimalNumber, matrix: np.ndarray, **kwargs):
        super().__init__(decimal_number, **kwargs)
        self.matrix = matrix
        self.initial_matrix = np.identity(2)

    def interpolate_mobject(self, alpha: float) -> None:
        """
        Interpolates the mobject by updating its value.
        alpha goes from 0 to 1.
        """
        # Interpolate between the identity matrix and the final matrix
        interpolated_matrix = self.initial_matrix * (1 - alpha) + self.matrix * alpha
        
        # Calculate the determinant of the interpolated matrix
        det = np.linalg.det(interpolated_matrix)
        
        # Update the DecimalNumber mobject's value
        self.mobject.set_value(det)


class GeometricDeterminant(LinearTransformationScene):
    """
    An animation showing the geometric interpretation of the determinant
    of a 2x2 matrix.
    """
    def __init__(self):
        super().__init__(
            show_basis_vectors=True,
            leave_ghost_vectors=True,
            show_coordinates=True,
        )

    def construct(self):
        # Define the transformation matrix
        matrix = np.array([[2, 1], [1, 3]])
        det = np.linalg.det(matrix)

        # Create the unit parallelogram (a square for the standard basis)
        unit_square = Polygon(
            ORIGIN, RIGHT, RIGHT + UP, UP,
            color=BLUE,
            fill_opacity=0.4,
            stroke_width=3
        )

        # Create a label for the original area
        original_area_label = MathTex("Original Area = 1", font_size=36)
        original_area_label.next_to(unit_square, DOWN, buff=0.2)

        # Create the matrix display
        matrix_mob = Matrix(matrix, h_buff=1.3).to_corner(UL, buff=0.4)
        matrix_label = MathTex("A =").next_to(matrix_mob, LEFT)

        # Create the determinant display that will update
        det_value = DecimalNumber(1.0, num_decimal_places=2, font_size=36)
        det_label = MathTex("det(A) = ", font_size=36).next_to(matrix_mob, DOWN, buff=0.3, aligned_edge=LEFT)
        det_value.next_to(det_label, RIGHT)
        det_group = VGroup(det_label, det_value)

        # Add initial objects to the scene
        self.add(unit_square, original_area_label)
        self.add(matrix_mob, matrix_label, det_group)
        
        # Make the unit square transformable
        self.add_transformable_mobject(unit_square)

        self.wait(1)

        # Animate the transformation
        self.play(
            self.apply_matrix(matrix),
            UpdateDeterminant(det_value, matrix, run_time=4),
            FadeOut(original_area_label, run_time=1),
            run_time=4
        )
        self.wait(1)

        # Create the final area label
        final_area_text = f"New Area = |det(A)| = {abs(det):.2f}"
        final_area_label = MathTex(final_area_text, font_size=36)
        final_area_label.next_to(unit_square, DOWN, buff=0.2)
        
        # Animate the appearance of the final label
        self.play(Write(final_area_label))
        self.wait(3)
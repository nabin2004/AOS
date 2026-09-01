from manim import *

class DeterminantAnimation(Scene):
    def construct(self):
        # Define the basis vectors
        u = Vector([1, 0]).set_color(RED)
        v = Vector([0, 1]).set_color(RED)

        # Create the unit parallelogram
        parallelogram = Polygon([0, 0], [1, 0], [1, 1], [0, 1], color=YELLOW)

        # Create the 2x2 matrix A
        matrix_A = Matrix([[2, 1], [1, 1]]).set_color(GREEN)

        # Create the labels
        original_area_label = Tex("Original Area = 1").set_color(BLUE)
        new_area_label = Tex("New Area = |det(A)|").set_color(BLUE)
        det_A_label = Tex("det(A) = 1").set_color(BLUE)

        # Create the determinant value
        det_A_value = DecimalNumber(1, num_decimal_places=2).set_color(BLUE)

        # Create the matrix values
        matrix_values = VGroup(
            Tex("2").set_color(GREEN),
            Tex("1").set_color(GREEN),
            Tex("1").set_color(GREEN),
            Tex("1").set_color(GREEN)
        )

        # Create the transformation
        transformation = self.apply_matrix(matrix_A, parallelogram)

        # Animate the transformation
        self.play(
            ApplyFunction(lambda x: x * matrix_A, parallelogram),
            run_time=2
        )

        # Update the determinant value
        det_A_value.update_value(matrix_A.get_determinant())

        # Update the new area label
        new_area_label.update(det_A_value.get_value())

        # Show the final state
        self.play(
            Write(original_area_label, run_time=0.5),
            Write(det_A_label, run_time=0.5),
            Write(matrix_values, run_time=0.5),
            Write(new_area_label, run_time=0.5),
            Write(det_A_value, run_time=0.5),
            run_time=1
        )

    def apply_matrix(self, matrix, parallelogram):
        # Apply the matrix to the parallelogram
        new_points = [
            matrix.get_column(0) + matrix.get_column(1),
            matrix.get_column(0) + matrix.get_column(1) + matrix.get_column(0),
            matrix.get_column(0) + matrix.get_column(1) + matrix.get_column(0) + matrix.get_column(1),
            matrix.get_column(0) + matrix.get_column(1)
        ]

        # Create the new parallelogram
        new_parallelogram = Polygon(
            new_points[0],
            new_points[1],
            new_points[2],
            new_points[3],
            color=YELLOW
        )

        # Return the new parallelogram
        return new_parallelogram
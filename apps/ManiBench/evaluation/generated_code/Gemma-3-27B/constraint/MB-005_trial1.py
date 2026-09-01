from manim import *

class DeterminantVisualization(Scene):
    def construct(self):
        # Define basis vectors
        u = Vector([1, 0], color=BLUE, buff=0)
        v = Vector([0, 1], color=GREEN, buff=0)

        # Create parallelogram
        parallelogram = Polygon(ORIGIN, u, u + v, v, color=YELLOW, opacity=0.7)
        area_label = Tex("Original Area = 1", color=BLUE).next_to(parallelogram, UP)

        self.play(Create(u), Create(v), Create(parallelogram), Write(area_label))
        self.wait(1)

        # Define matrix A
        matrix_a = Matrix([[2, 1], [1, 3]], element_color=RED)
        matrix_label = Tex("Matrix A = ", color=RED).next_to(matrix_a, LEFT)
        self.play(Write(matrix_label), Write(matrix_a))
        self.wait(1)

        # Calculate determinant
        det_a = 2 * 3 - 1 * 1
        det_label = Tex("det(A) = ", color=PURPLE).next_to(matrix_a, DOWN)
        det_value = Tex(f"{det_a}", color=PURPLE).next_to(det_label, RIGHT)
        self.play(Write(det_label), Write(det_value))
        self.wait(1)

        # Create grid
        grid = VGroup(*[Line(x * RIGHT + y * UP, x * RIGHT + (y + 1) * UP, color=GRAY, stroke_width=0.5)
                        for x in range(-3, 3)]
                       for y in range(-3, 3)])

        # Apply transformation
        transformed_parallelogram = VGroup()
        transformed_u = u.copy().transform(matrix_a)
        transformed_v = v.copy().transform(matrix_a)
        transformed_parallelogram.add(Polygon(ORIGIN, transformed_u, transformed_u + transformed_v, transformed_v, color=YELLOW, opacity=0.7))

        transformed_grid = VGroup(*[Line(x * RIGHT + y * UP, x * RIGHT + (y + 1) * UP, color=GRAY, stroke_width=0.5)
                                    for x in range(-3, 3)]
                                   for y in range(-3, 3)])
        transformed_grid.apply_matrix(matrix_a)

        # Animate transformation
        self.play(
            Transform(parallelogram, transformed_parallelogram),
            Transform(grid, transformed_grid),
            det_value.animate.set_value(str(abs(det_a)))
        )
        self.wait(2)

        # New area label
        new_area_label = Tex(f"New Area = |det(A)| = {abs(det_a)}", color=BLUE).next_to(transformed_parallelogram, UP)
        self.play(Write(new_area_label))
        self.wait(2)
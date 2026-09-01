from manim import *

class EigenvectorsTransformation(Scene):
    def construct(self):
        # Create 2D coordinate grid
        grid = NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            x_length=10,
            y_length=10,
            axis_config={"include_tip": False},
        )
        self.add(grid)

        # Highlight basis vectors e₁ and e₂
        e1 = grid.get_vector(5, 0)
        e1.set_color(RED)
        e1_label = Tex("e₁").next_to(e1, RIGHT)
        e2 = grid.get_vector(0, 5)
        e2.set_color(RED)
        e2_label = Tex("e₂").next_to(e2, UP)
        self.add(e1, e1_label, e2, e2_label)

        # Define 2x2 matrix A
        A = Matrix([[2, 1], [1, 1]])

        # Create eigenvectors and eigenvalues
        lambda1 = 3
        lambda2 = 0.5
        v1 = grid.get_vector(1, 1)
        v1.set_color(BLUE)
        v1_label = Tex("v₁").next_to(v1, RIGHT)
        v2 = grid.get_vector(1, -1)
        v2.set_color(BLUE)
        v2_label = Tex("v₂").next_to(v2, RIGHT)
        self.add(v1, v1_label, v2, v2_label)

        # Animate transformation
        self.play(
            grid.animate.apply_matrix(A),
            run_time=2,
        )

        # Highlight eigenvectors after transformation
        self.play(
            v1.animate.set_color(RED),
            v2.animate.set_color(RED),
            run_time=0.5,
        )

        # Display eigenvalues
        eigenvalues = Tex("λ₁ = 3, λ₂ = 0.5").next_to(grid, DOWN)
        self.add(eigenvalues)

        # Highlight eigenvectors as 'special'
        special_label = Tex("Eigenvectors: special vectors that only change length").next_to(grid, DOWN)
        self.add(special_label)
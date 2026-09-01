from manim import *
import numpy as np

class EigenvectorsAnimation(LinearTransformationScene):
    """
    An animation demonstrating the concept of eigenvectors and eigenvalues
    for a 2x2 matrix transformation.
    """
    def __init__(self):
        super().__init__(
            show_basis_vectors=True,
            include_foreground_plane=True,
            foreground_plane_kwargs={
                "x_range": np.array([-7, 7, 1]),
                "y_range": np.array([-4, 4, 1]),
                "faded_line_ratio": 4,
            },
            background_plane_kwargs={
                "x_range": np.array([-7, 7, 1]),
                "y_range": np.array([-4, 4, 1]),
                "faded_line_ratio": 4,
            },
        )
        # Define the 2x2 transformation matrix
        self.matrix = np.array([[3, 1], [1, 2]])

    def construct(self):
        # 1. Display the matrix
        matrix_title = MathTex("A = ").to_corner(UL).add_background_rectangle()
        matrix_mob = Matrix(self.matrix, h_buff=1.2).next_to(matrix_title, RIGHT).add_background_rectangle()
        self.add(matrix_title, matrix_mob)

        # 2. Calculate eigenvalues and eigenvectors
        eigenvalues, eigenvectors_matrix = np.linalg.eig(self.matrix)
        lambda1, lambda2 = eigenvalues
        v1_dir, v2_dir = eigenvectors_matrix[:, 0], eigenvectors_matrix[:, 1]

        # Normalize eigenvectors for consistent visualization
        v1_start = 2 * v1_dir / np.linalg.norm(v1_dir)
        v2_start = 2 * v2_dir / np.linalg.norm(v2_dir)
        
        # A "normal" vector that is not an eigenvector
        v_other_start = np.array([1, -1])

        # 3. Create vector mobjects
        v1 = Vector(v1_start, color=RED)
        v2 = Vector(v2_start, color=BLUE)
        v_other = Vector(v_other_start, color=WHITE)

        # Create lines representing the span of eigenvectors
        line1 = Line(v1_start * -5, v1_start * 5, color=RED, stroke_width=2, opacity=0.7)
        line2 = Line(v2_start * -5, v2_start * 5, color=BLUE, stroke_width=2, opacity=0.7)

        # 4. Create labels for vectors and eigenvalues
        v1_lab = MathTex("\\vec{v}_1", color=RED, font_size=36)
        lambda1_lab = MathTex(f"\\lambda_1 \\approx {lambda1:.2f}", color=RED, font_size=36)
        label_group1 = VGroup(v1_lab, lambda1_lab).arrange(DOWN, buff=0.1)
        label_group1.add_updater(lambda m: m.next_to(v1.get_tip(), UR, buff=0.1))

        v2_lab = MathTex("\\vec{v}_2", color=BLUE, font_size=36)
        lambda2_lab = MathTex(f"\\lambda_2 \\approx {lambda2:.2f}", color=BLUE, font_size=36)
        label_group2 = VGroup(v2_lab, lambda2_lab).arrange(DOWN, buff=0.1)
        label_group2.add_updater(lambda m: m.next_to(v2.get_tip(), UL, buff=0.1))

        v_other_lab = MathTex("\\vec{x}", color=WHITE, font_size=36)
        v_other_lab.add_updater(lambda m: m.next_to(v_other.get_tip(), UP, buff=0.1))

        # Add basis vector labels
        i_hat_label = self.get_i_hat_label()
        j_hat_label = self.get_j_hat_label()
        self.add(i_hat_label, j_hat_label)

        # 5. Add all transformable mobjects to the scene
        self.add_transformable_mobject(v1, v2, v_other, line1, line2)
        self.add(label_group1, label_group2, v_other_lab)

        self.wait(1)

        # 6. Apply the matrix transformation
        self.apply_matrix(self.matrix, run_time=3)
        self.wait(1)

        # 7. Highlight the special property of eigenvectors
        explanation_text = Text(
            "Eigenvectors stay on their own span, only changing length.",
            font_size=28
        ).to_corner(UR).add_background_rectangle()
        
        # Show that Av = λv
        eq1 = MathTex(
            "A\\vec{v}_1", "=", f"{lambda1:.2f}", "\\vec{v}_1",
            font_size=36
        ).next_to(explanation_text, DOWN, buff=0.2).align_to(explanation_text, LEFT)
        eq1.set_color_by_tex_to_color_map({"A\\vec{v}_1": RED, "\\vec{v}_1": RED})
        
        eq2 = MathTex(
            "A\\vec{v}_2", "=", f"{lambda2:.2f}", "\\vec{v}_2",
            font_size=36
        ).next_to(eq1, DOWN, buff=0.2).align_to(eq1, LEFT)
        eq2.set_color_by_tex_to_color_map({"A\\vec{v}_2": BLUE, "\\vec{v}_2": BLUE})

        self.play(Write(explanation_text))
        self.wait(0.5)
        self.play(Write(eq1))
        self.play(Write(eq2))
        
        # Flash the eigenvectors to draw attention
        self.play(
            Flash(v1, color=RED, line_length=0.3, flash_radius=0.4),
            Flash(v2, color=BLUE, line_length=0.3, flash_radius=0.4),
            run_time=2
        )
        self.wait(3)
from manim import *

class EigenVectorTransformation(LinearTransformationScene):
    def __init__(self, **kwargs):
        LinearTransformationScene.__init__(
            self,
            include_background_plane=True,
            include_foreground_plane=True,
            show_coordinates=True,
            show_basis_vectors=True,
            basis_vector_stroke_width=6,
            leave_ghost_vectors=False,
            **kwargs
        )

    def construct(self):
        # Define the transformation matrix
        matrix = [[2, 1], [1, 2]]
        A = np.array(matrix)

        # Title
        title = Text("Eigenvectors under Matrix Transformation", font_size=36)
        title.to_edge(UP)
        self.add(title)

        # Basis vectors e1 and e2
        e1_label = MathTex(r"\mathbf{e}_1", color=X_COLOR).next_to(self.get_vector([1, 0]), DOWN)
        e2_label = MathTex(r"\mathbf{e}_2", color=Y_COLOR).next_to(self.get_vector([0, 1]), LEFT)
        self.add(e1_label, e2_label)

        # Eigenvectors of matrix A = [[2,1],[1,2]]
        # Eigenvalues: λ₁ = 3, λ₂ = 1
        # Eigenvectors: v₁ = [1, 1], v₂ = [-1, 1]
        eigenvector_1 = self.get_vector([1, 1], color=RED, stroke_width=6)
        eigenvector_2 = self.get_vector([-1, 1], color=BLUE, stroke_width=6)

        v1_label = MathTex(r"\mathbf{v}_1", color=RED).next_to(eigenvector_1, RIGHT)
        v2_label = MathTex(r"\mathbf{v}_2", color=BLUE).next_to(eigenvector_2, LEFT)

        lambda1_label = MathTex(r"\lambda_1 = 3", color=RED).to_edge(LEFT).shift(UP * 2)
        lambda2_label = MathTex(r"\lambda_2 = 1", color=BLUE).to_edge(LEFT).shift(UP * 1)

        self.add(eigenvector_1, eigenvector_2, v1_label, v2_label)
        self.add(lambda1_label, lambda2_label)

        # Add a random vector to show general behavior
        random_vector = self.get_vector([2, 0.5], color=GREEN)
        random_label = MathTex(r"\mathbf{v}", color=GREEN).next_to(random_vector, DOWN)
        self.add(random_vector, random_label)

        # Pause before transformation
        self.wait(2)

        # Apply transformation smoothly over 2 seconds
        self.apply_matrix(matrix, run_time=2)

        # After transformation, show that eigenvectors are scaled but not rotated
        final_eigenvector_1 = self.get_vector([3, 3], color=RED, stroke_width=6)
        final_eigenvector_2 = self.get_vector([-1, 1], color=BLUE, stroke_width=6)

        # Update labels after transformation
        new_v1_label = MathTex(r"\lambda_1 \mathbf{v}_1", color=RED).next_to(final_eigenvector_1, RIGHT)
        new_v2_label = MathTex(r"\lambda_2 \mathbf{v}_2", color=BLUE).next_to(final_eigenvector_2, LEFT)

        self.play(
            Transform(eigenvector_1, final_eigenvector_1),
            Transform(eigenvector_2, final_eigenvector_2),
            Transform(v1_label, new_v1_label),
            Transform(v2_label, new_v2_label),
            run_time=1
        )

        # Highlight that eigenvectors are special
        special_text = Text("Eigenvectors: Only scaled, not rotated!", color=YELLOW).to_edge(DOWN)
        self.play(Write(special_text), run_time=1.5)

        # Hold final frame
        self.wait(2)
from manim import *

class DeterminantVisualization(Scene):
    def construct(self):
        # Create axes
        axes = Axes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            axis_config={"color": BLUE},
        )
        
        # Define basis vectors u and v
        u = np.array([1, 0])
        v = np.array([0, 1])
        
        # Create original parallelogram
        parallelogram = Polygon(ORIGIN, u, u + v, v, color=GREEN)
        parallelogram.set_fill(GREEN, opacity=0.5)
        
        # Create labels for area
        original_area_label = MathTex("A_{\\text{original}} = 1").to_edge(UP)
        new_area_label = MathTex(r"A_{\text{new}} = |\det(A)|").next_to(original_area_label, DOWN)
        
        # Create matrix A
        A = Matrix([[1, -1], [1, 2]])
        A.next_to(new_area_label, RIGHT)
        
        # Create determinant text
        det_text = MathTex(r"\det(A)").next_to(A, UP)
        
        # Animate creation of axes and parallelogram
        self.play(Create(axes))
        self.play(FadeIn(parallelogram))
        self.play(Write(original_area_label))
        
        # Transform parallelogram with matrix A
        transformed_parallelogram = parallelogram.copy().apply_matrix(A.get_value())
        self.play(Transform(parallelogram, transformed_parallelogram))
        
        # Update area label
        self.play(ReplacementTransform(original_area_label, new_area_label))
        
        # Add matrix A and determinant text
        self.play(FadeIn(A), Write(det_text))
        
        # Update determinant text dynamically
        det_value = A.get_determinant()
        det_value_tex = MathTex(f"{abs(det_value):.2f}").move_to(det_text)
        self.play(Transform(det_text, det_value_tex))
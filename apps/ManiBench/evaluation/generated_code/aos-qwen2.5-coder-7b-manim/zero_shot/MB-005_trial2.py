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
        original_area_label = MathTex("A_{\\text{original}} = 1").next_to(parallelogram, UP)
        new_area_label = MathTex(r"A_{\text{new}} = |\det(A)|").next_to(original_area_label, DOWN)
        
        # Create matrix A
        A = Matrix([[1, 1], [0, 1]]).scale(0.8).to_edge(RIGHT)
        
        # Add all elements to scene
        self.play(Create(axes))
        self.play(Create(parallelogram), Write(original_area_label))
        self.wait()
        
        # Transform parallelogram with matrix A
        transformed_parallelogram = parallelogram.copy().apply_matrix(A.get_value())
        self.play(Transform(parallelogram, transformed_parallelogram))
        
        # Update area label
        self.play(ReplacementTransform(original_area_label, new_area_label))
        
        # Show matrix A values
        self.play(FadeIn(A))
        self.wait()
        
        # Animate determinant calculation
        det_text = MathTex(r"\det(A) = \begin{vmatrix} 1 & 1 \\ 0 & 1 \end{vmatrix} = 1").next_to(A, RIGHT)
        self.play(Write(det_text))
        self.wait()
        
        # Highlight determinant value
        det_box = SurroundingRectangle(det_text[0][9:10], color=YELLOW)
        self.play(Create(det_box))
        self.wait()
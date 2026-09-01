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
        A = Matrix([[1, 1], [0, 1]]).scale(0.8).to_edge(RIGHT)
        
        # Add all elements to scene
        self.play(Create(axes))
        self.play(Create(parallelogram))
        self.play(Write(original_area_label))
        self.wait()
        
        # Transform parallelogram with matrix A
        transformed_parallelogram = parallelogram.copy().apply_matrix(A.get_value())
        
        # Update area label
        new_area_value = abs(np.linalg.det(A.get_value()))
        new_area_label = MathTex(f"A_{\\text{{new}}} = {new_area_value:.2f}").next_to(original_area_label, DOWN)
        
        # Animate transformation
        self.play(Transform(parallelogram, transformed_parallelogram))
        self.play(ReplacementTransform(original_area_label, new_area_label))
        self.wait()
        
        # Show matrix A
        self.play(FadeIn(A))
        self.wait()
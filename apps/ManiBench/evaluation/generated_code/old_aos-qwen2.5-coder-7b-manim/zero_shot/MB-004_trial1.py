from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # Create axes and basis vectors
        axes = Axes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            axis_config={"color": BLUE},
        )
        e1 = Arrow(start=ORIGIN, end=RIGHT*2, color=RED)
        e2 = Arrow(start=ORIGIN, end=UP*2, color=GREEN)
        
        # Label basis vectors
        label_e1 = MathTex(r"\mathbf{e}_1").next_to(e1.get_end(), RIGHT)
        label_e2 = MathTex(r"\mathbf{e}_2").next_to(e2.get_end(), UP)
        
        # Create matrix A visualization
        matrix_A = Matrix([[1, -1], [0.5, 1]], element_color=WHITE)
        matrix_label = Tex("Matrix $A$").next_to(matrix_A, DOWN)
        
        # Create eigenvalue labels
        lambda1 = MathTex(r"\lambda_1", color=RED).to_edge(LEFT)
        lambda2 = MathTex(r"\lambda_2", color=BLUE).to_edge(RIGHT)
        
        # Group all elements
        group = VGroup(axes, e1, e2, label_e1, label_e2, matrix_A, matrix_label, lambda1, lambda2)
        
        # Animate creation of axes and basis vectors
        self.play(Create(axes))
        self.play(GrowArrow(e1), GrowArrow(e2))
        self.play(Write(label_e1), Write(label_e2))
        
        # Animate matrix A
        self.play(FadeIn(matrix_A), Write(matrix_label))
        
        # Animate eigenvalue labels
        self.play(Write(lambda1), Write(lambda2))
        
        # Transform basis vectors into eigenvectors
        e1_transformed = Arrow(start=ORIGIN, end=RIGHT*3 + UP*1, color=RED)
        e2_transformed = Arrow(start=ORIGIN, end=RIGHT*1 + UP*2, color=BLUE)
        
        self.play(Transform(e1, e1_transformed), Transform(e2, e2_transformed))
        
        # Highlight eigenvectors
        self.play(
            e1.animate.set_color(YELLOW),
            e2.animate.set_color(YELLOW),
            run_time=1
        )
        
        # Show transformation effect
        transformed_grid = axes.copy()
        transformed_grid.apply_matrix(np.array([
            [1.5, -0.5],
            [0.5, 1.5]
        ]))
        
        self.play(Transform(axes, transformed_grid), run_time=2)
        
        # Final highlight
        self.play(
            e1.animate.set_color(RED),
            e2.animate.set_color(BLUE),
            run_time=1
        )
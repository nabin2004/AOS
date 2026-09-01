from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # Create axes and basis vectors
        axes = Axes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            axis_config={"color": BLUE},
        )
        e1 = Arrow(start=ORIGIN, end=RIGHT*2, color=YELLOW)
        e2 = Arrow(start=ORIGIN, end=UP*2, color=YELLOW)
        
        # Label basis vectors
        label_e1 = MathTex(r"\mathbf{e}_1").next_to(e1.get_end(), RIGHT)
        label_e2 = MathTex(r"\mathbf{e}_2").next_to(e2.get_end(), UP)
        
        # Create matrix A visualization
        matrix_A = Matrix([[1, 0], [0, 2]], element_color=WHITE)
        matrix_label = Tex("Matrix $A$").next_to(matrix_A, DOWN)
        
        # Create eigenvalue labels
        lambda1 = MathTex(r"\lambda_1 = 1", color=RED).to_edge(LEFT)
        lambda2 = MathTex(r"\lambda_2 = 2", color=BLUE).to_edge(RIGHT)
        
        # Group all elements
        group = VGroup(axes, e1, e2, label_e1, label_e2, matrix_A, matrix_label, lambda1, lambda2)
        
        # Animate creation of elements
        self.play(Create(axes))
        self.play(GrowArrow(e1), GrowArrow(e2), Write(label_e1), Write(label_e2))
        self.wait(0.5)
        self.play(FadeIn(matrix_A), Write(matrix_label))
        self.wait(0.5)
        self.play(Write(lambda1), Write(lambda2))
        self.wait()
        
        # Transform vectors
        transformed_e1 = Arrow(start=ORIGIN, end=RIGHT*1.5, color=RED)
        transformed_e2 = Arrow(start=ORIGIN, end=UP*2, color=BLUE)
        
        self.play(Transform(e1, transformed_e1), Transform(e2, transformed_e2))
        self.wait()
        
        # Highlight eigenvectors
        self.play(
            e1.animate.set_color(YELLOW),
            e2.animate.set_color(YELLOW),
            run_time=1
        )
        self.wait()
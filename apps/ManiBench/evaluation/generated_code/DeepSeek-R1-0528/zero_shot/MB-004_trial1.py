from manim import *

class EigenvectorTransformation(Scene):
    def construct(self):
        # Define the transformation matrix
        matrix_A = [[2, 1], 
                    [1, 2]]
        
        # Create coordinate grid
        grid = NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            background_line_style={
                "stroke_color": BLUE_D,
                "stroke_width": 1,
                "stroke_opacity": 0.3
            }
        )
        
        # Create basis vectors
        e1 = Vector([1, 0], color=YELLOW)
        e1_label = MathTex("\\mathbf{e}_1", color=YELLOW).next_to(e1.get_end(), RIGHT, buff=0.1)
        
        e2 = Vector([0, 1], color=GREEN)
        e2_label = MathTex("\\mathbf{e}_2", color=GREEN).next_to(e2.get_end(), UP, buff=0.1)
        
        # Create eigenvectors
        v1 = Vector([1, 1], color=RED)
        v1_label = MathTex("\\mathbf{v}_1", color=RED).next_to(v1.get_end(), UR, buff=0.1)
        lambda1_text = MathTex("\\lambda_1 = 3", color=RED).to_corner(UL)
        
        v2 = Vector([1, -1], color=BLUE)
        v2_label = MathTex("\\mathbf{v}_2", color=BLUE).next_to(v2.get_end(), DR, buff=0.1)
        lambda2_text = MathTex("\\lambda_2 = 1", color=BLUE).next_to(lambda1_text, DOWN)
        
        # Create transformation description
        matrix_tex = MathTex("A = \\begin{bmatrix} 2 & 1 \\\\ 1 & 2 \\end{bmatrix}").to_corner(UR)
        
        # Initial setup
        self.add(grid, e1, e2, e1_label, e2_label)
        self.play(
            Create(v1), Write(v1_label),
            Create(v2), Write(v2_label),
            Write(lambda1_text), Write(lambda2_text),
            Write(matrix_tex)
        )
        self.wait(1)
        
        # Group transformable objects
        transform_group = VGroup(grid, e1, e2, v1, v2)
        
        # Apply matrix transformation
        self.play(
            ApplyMatrix(matrix_A, transform_group),
            v1_label.animate.next_to(v1.get_end(), UR, buff=0.1),
            v2_label.animate.next_to(v2.get_end(), DR, buff=0.1),
            run_time=2
        )
        
        # Highlight eigenvectors
        self.play(
            v1.animate.set_stroke(width=8),
            v2.animate.set_stroke(width=8),
            Flash(v1, color=RED, line_length=0.3, num_lines=12),
            Flash(v2, color=BLUE, line_length=0.3, num_lines=12),
            run_time=1.5
        )
        
        # Add explanation text
        eigen_text = Text("Eigenvectors only scale!", font_size=36).to_edge(DOWN)
        self.play(Write(eigen_text))
        self.wait(2)
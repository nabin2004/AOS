from manim import *
import numpy as np

class EigenvectorTransformation(Scene):
    def construct(self):
        # Define the transformation matrix
        A = np.array([[2, 1], [1, 2]])
        
        # Calculate eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eig(A)
        lambda1, lambda2 = eigenvalues
        v1, v2 = eigenvectors[:, 0], eigenvectors[:, 1]
        
        # Normalize eigenvectors for display
        v1_normalized = v1 / np.linalg.norm(v1) * 2
        v2_normalized = v2 / np.linalg.norm(v2) * 2
        
        # Create coordinate grid
        grid = NumberPlane(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            background_line_style={
                "stroke_color": BLUE_E,
                "stroke_width": 1,
                "stroke_opacity": 0.6
            }
        )
        
        # Create basis vectors
        e1 = Arrow(ORIGIN, RIGHT, color=GREEN, buff=0)
        e2 = Arrow(ORIGIN, UP, color=GREEN, buff=0)
        e1_label = MathTex("\\mathbf{e_1}", color=GREEN).next_to(e1.get_end(), DOWN)
        e2_label = MathTex("\\mathbf{e_2}", color=GREEN).next_to(e2.get_end(), LEFT)
        
        # Create eigenvectors
        eigen1_arrow = Arrow(ORIGIN, v1_normalized, color=RED, buff=0, stroke_width=6)
        eigen2_arrow = Arrow(ORIGIN, v2_normalized, color=BLUE, buff=0, stroke_width=6)
        
        # Create eigenvector lines (to show they stay on same line)
        eigen1_line = Line(-3 * v1_normalized, 3 * v1_normalized, color=RED, stroke_opacity=0.3)
        eigen2_line = Line(-3 * v2_normalized, 3 * v2_normalized, color=BLUE, stroke_opacity=0.3)
        
        # Create some regular vectors to show rotation
        regular_vectors = VGroup()
        for angle in [PI/6, PI/3, 2*PI/3, 5*PI/6]:
            vec = Arrow(ORIGIN, 1.5 * np.array([np.cos(angle), np.sin(angle), 0]), 
                       color=YELLOW, buff=0, stroke_width=3)
            regular_vectors.add(vec)
        
        # Labels for eigenvalues and eigenvectors
        eigen1_label = MathTex("\\mathbf{v_1}", color=RED).next_to(eigen1_arrow.get_end(), UR, buff=0.1)
        eigen2_label = MathTex("\\mathbf{v_2}", color=BLUE).next_to(eigen2_arrow.get_end(), UL, buff=0.1)
        
        lambda1_text = MathTex(f"\\lambda_1 = {lambda1:.2f}", color=RED).to_corner(UL)
        lambda2_text = MathTex(f"\\lambda_2 = {lambda2:.2f}", color=BLUE).next_to(lambda1_text, DOWN)
        
        # Matrix display
        matrix_text = MathTex("A = \\begin{pmatrix} 2 & 1 \\\\ 1 & 2 \\end{pmatrix}").to_corner(UR)
        
        # Title
        title = Text("Eigenvector Transformation", font_size=36).to_edge(UP)
        
        # Initial setup
        self.add(grid)
        self.play(
            Create(e1), Create(e2),
            Write(e1_label), Write(e2_label),
            Write(title),
            Write(matrix_text)
        )
        self.wait(1)
        
        # Add eigenvector lines first
        self.play(Create(eigen1_line), Create(eigen2_line))
        
        # Add vectors
        self.play(
            Create(eigen1_arrow), Create(eigen2_arrow),
            Create(regular_vectors),
            Write(eigen1_label), Write(eigen2_label),
            Write(lambda1_text), Write(lambda2_text)
        )
        self.wait(1)
        
        # Explanation text
        explanation1 = Text("Regular vectors (yellow) will rotate and scale", 
                           font_size=24, color=YELLOW).to_edge(DOWN)
        explanation2 = Text("Eigenvectors (red/blue) only scale along their direction", 
                           font_size=24).next_to(explanation1, UP)
        
        self.play(Write(explanation2), Write(explanation1))
        self.wait(2)
        
        # Remove explanations
        self.play(FadeOut(explanation1), FadeOut(explanation2))
        
        # Apply transformation
        self.play(
            ApplyMatrix(A, grid),
            ApplyMatrix(A, e1),
            ApplyMatrix(A, e2),
            ApplyMatrix(A, regular_vectors),
            ApplyMatrix(A, eigen1_arrow),
            ApplyMatrix(A, eigen2_arrow),
            run_time=2
        )
        
        # Update labels after transformation
        new_e1_label = MathTex("A\\mathbf{e_1}", color=GREEN).next_to(e1.get_end(), DOWN)
        new_e2_label = MathTex("A\\mathbf{e_2}", color=GREEN).next_to(e2.get_end(), LEFT)
        
        self.play(
            Transform(e1_label, new_e1_label),
            Transform(e2_label, new_e2_label)
        )
        
        # Highlight that eigenvectors stayed on their lines
        highlight_text = Text("Eigenvectors stayed on their original lines!", 
                             font_size=28, color=WHITE).to_edge(DOWN)
        
        self.play(
            Indicate(eigen1_line, color=RED, scale_factor=1.2),
            Indicate(eigen2_line, color=BLUE, scale_factor=1.2),
            Write(highlight_text)
        )
        self.wait(1)
        
        # Show scaling factors
        scale_text1 = MathTex(f"\\text{{Scaled by }} \\lambda_1 = {lambda1:.2f}", 
                             color=RED, font_size=24).next_to(lambda2_text, DOWN)
        scale_text2 = MathTex(f"\\text{{Scaled by }} \\lambda_2 = {lambda2:.2f}", 
                             color=BLUE, font_size=24).next_to(scale_text1, DOWN)
        
        self.play(Write(scale_text1), Write(scale_text2))
        self.wait(3)
        
        # Final highlight of the special property
        final_text = Text("This is what makes eigenvectors special!", 
                         font_size=32, color=GOLD).move_to(highlight_text.get_center())
        
        self.play(Transform(highlight_text, final_text))
        self.wait(2)
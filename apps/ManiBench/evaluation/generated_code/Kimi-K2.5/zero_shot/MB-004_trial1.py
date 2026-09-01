from manim import *
import numpy as np

class EigenvectorAnimation(Scene):
    def construct(self):
        # Define transformation matrix A = [[3, 1], [1, 3]]
        # This matrix has eigenvalues 4 and 2 with eigenvectors [1,1] and [1,-1]
        matrix = np.array([[3, 1], [1, 3]])
        
        # Create coordinate grid
        plane = NumberPlane(
            x_range=[-8, 8, 1],
            y_range=[-8, 8, 1],
            background_line_style={
                "stroke_color": BLUE_D,
                "stroke_width": 1,
                "stroke_opacity": 0.4
            },
            axis_config={"stroke_color": GREY}
        )
        
        # Basis vectors e1 and e2
        e1 = Vector(RIGHT * 2, color=YELLOW, buff=0)
        e2 = Vector(UP * 2, color=YELLOW, buff=0)
        e1_label = MathTex(r"\mathbf{e}_1", color=YELLOW).next_to(e1.get_end(), DR, buff=0.1)
        e2_label = MathTex(r"\mathbf{e}_2", color=YELLOW).next_to(e2.get_end(), UL, buff=0.1)
        
        # Eigenvectors (normalized to length 2 for visibility)
        # v1 along [1, 1] (red, eigenvalue 4)
        # v2 along [1, -1] (blue, eigenvalue 2)
        v1_dir = np.array([1, 1]) / np.sqrt(2)
        v2_dir = np.array([1, -1]) / np.sqrt(2)
        
        ev1 = Vector(v1_dir * 2, color=RED, buff=0)
        ev2 = Vector(v2_dir * 2, color=BLUE, buff=0)
        
        # Other vectors (green) that will rotate under transformation
        other_vectors = VGroup()
        angles = [20, 50, 110, 160]  # Various directions
        for angle in angles:
            rad = np.radians(angle)
            vec = np.array([np.cos(rad), np.sin(rad)]) * 1.8
            other_vectors.add(Vector(vec, color=GREEN, buff=0))
        
        # Labels for eigenvectors
        ev1_label = MathTex(r"\mathbf{v}_1", color=RED).next_to(ev1.get_end(), UR, buff=0.1)
        ev2_label = MathTex(r"\mathbf{v}_2", color=BLUE).next_to(ev2.get_end(), DR, buff=0.1)
        
        # Matrix label
        matrix_tex = MathTex(r"A = \begin{bmatrix} 3 & 1 \\ 1 & 3 \end{bmatrix}")
        matrix_tex.to_corner(UL).shift(RIGHT * 0.5)
        
        # Title
        title = Text("Eigenvector Transformation", font_size=36)
        title.to_edge(UP)
        
        # Scene 1: Setup grid and basis
        self.play(Create(plane), run_time=1)
        self.play(
            GrowArrow(e1), GrowArrow(e2),
            Write(e1_label), Write(e2_label),
            run_time=1
        )
        self.wait(0.5)
        
        # Scene 2: Show eigenvectors and other vectors
        self.play(
            GrowArrow(ev1), GrowArrow(ev2),
            Write(ev1_label), Write(ev2_label),
            *[GrowArrow(v) for v in other_vectors],
            run_time=1.5
        )
        self.play(Write(matrix_tex), Write(title))
        self.wait(0.5)
        
        # Scene 3: Apply transformation (2 seconds)
        # Fade out labels before transforming (text shouldn't stretch)
        all_old_labels = [e1_label, e2_label, ev1_label, ev2_label]
        
        self.play(
            plane.animate.apply_matrix(matrix),
            e1.animate.apply_matrix(matrix),
            e2.animate.apply_matrix(matrix),
            ev1.animate.apply_matrix(matrix),
            ev2.animate.apply_matrix(matrix),
            *[v.animate.apply_matrix(matrix) for v in other_vectors],
            *[FadeOut(l) for l in all_old_labels],
            run_time=2,
            rate_func=smooth
        )
        
        # Scene 4: New labels at transformed positions
        new_e1_label = MathTex(r"\mathbf{e}_1", color=YELLOW).next_to(e1.get_end(), DR, buff=0.1)
        new_e2_label = MathTex(r"\mathbf{e}_2", color=YELLOW).next_to(e2.get_end(), UL, buff=0.1)
        new_ev1_label = MathTex(r"\mathbf{v}_1", color=RED).next_to(ev1.get_end(), UR, buff=0.1)
        new_ev2_label = MathTex(r"\mathbf{v}_2", color=BLUE).next_to(ev2.get_end(), DR, buff=0.1)
        
        # Eigenvalue labels
        lambda1_tex = MathTex(r"\lambda_1 = 4", color=RED).scale(0.8)
        lambda2_tex = MathTex(r"\lambda_2 = 2", color=BLUE).scale(0.8)
        lambda1_tex.next_to(ev1.get_end(), RIGHT)
        lambda2_tex.next_to(ev2.get_end(), LEFT)
        
        self.play(
            Write(new_e1_label), Write(new_e2_label),
            Write(new_ev1_label), Write(new_ev2_label),
            run_time=0.5
        )
        
        # Scene 5: Highlight eigenvectors stay on same line
        # Draw lines through origin in direction of eigenvectors
        line1 = DashedLine(
            plane.c2p(-6, -6), plane.c2p(6, 6),
            color=RED, stroke_opacity=0.6
        )
        line2 = DashedLine(
            plane.c2p(-6, 6), plane.c2p(6, -6),
            color=BLUE, stroke_opacity=0.6
        )
        
        self.play(Create(line1), Create(line2), run_time=1)
        self.play(
            Write(lambda1_tex),
            Write(lambda2_tex),
            run_time=1
        )
        
        # Scene 6: Emphasize that eigenvectors are special
        special_text = Text("Eigenvectors only scale (no rotation)!", font_size=32)
        special_text.to_edge(DOWN)
        
        # Highlight one green vector to show it rotated
        example_vec = other_vectors[0]
        
        self.play(
            example_vec.animate.set_color(YELLOW).set_stroke(width=8),
            run_time=0.5
        )
        self.play(
            example_vec.animate.set_color(GREEN).set_stroke(width=4),
            run_time=0.5
        )
        
        self.play(Write(special_text), run_time=1)
        
        # Final emphasis: Scale eigenvectors to show eigenvalues visually
        self.play(
            Circumscribe(ev1, color=RED),
            Circumscribe(ev2, color=BLUE),
            run_time=1.5
        )
        
        self.wait(2)
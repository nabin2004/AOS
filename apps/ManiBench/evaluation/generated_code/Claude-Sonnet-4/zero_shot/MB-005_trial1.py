from manim import *
import numpy as np

class DeterminantGeometry(Scene):
    def construct(self):
        # Define the transformation matrix
        A = np.array([[2, 1], [0.5, 1.5]])
        det_A = np.linalg.det(A)
        
        # Create coordinate system
        axes = Axes(
            x_range=[-1, 4, 1],
            y_range=[-1, 3, 1],
            x_length=6,
            y_length=4,
            axis_config={"color": GRAY}
        )
        
        # Original basis vectors
        u_vec = np.array([1, 0, 0])
        v_vec = np.array([0, 1, 0])
        
        # Create unit parallelogram
        parallelogram = Polygon(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(1, 0),
            axes.coords_to_point(1, 1),
            axes.coords_to_point(0, 1),
            fill_opacity=0.3,
            fill_color=BLUE,
            stroke_color=BLUE,
            stroke_width=3
        )
        
        # Basis vectors
        u_arrow = Arrow(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(1, 0),
            color=RED,
            buff=0,
            stroke_width=4
        )
        v_arrow = Arrow(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(0, 1),
            color=GREEN,
            buff=0,
            stroke_width=4
        )
        
        # Labels for basis vectors
        u_label = MathTex(r"\vec{u}", color=RED).next_to(u_arrow, DOWN)
        v_label = MathTex(r"\vec{v}", color=GREEN).next_to(v_arrow, LEFT)
        
        # Original area label
        original_area_label = Text("Original Area = 1", font_size=24).to_edge(UL)
        
        # Matrix display
        matrix_tex = MathTex(
            r"A = \begin{bmatrix} 2 & 1 \\ 0.5 & 1.5 \end{bmatrix}",
            font_size=36
        ).to_edge(UR)
        
        # Determinant value tracker
        det_tracker = ValueTracker(1)
        det_label = always_redraw(lambda: 
            Text(f"New Area = |det(A)| = {det_tracker.get_value():.2f}", 
                 font_size=24).next_to(original_area_label, DOWN, buff=0.3)
        )
        
        # Add initial elements
        self.add(axes)
        self.play(
            Create(parallelogram),
            Create(u_arrow),
            Create(v_arrow),
            Write(u_label),
            Write(v_label),
            Write(original_area_label),
            Write(matrix_tex)
        )
        self.wait(1)
        
        # Show determinant label
        self.play(Write(det_label))
        self.wait(1)
        
        # Transform the parallelogram
        # New vertices after transformation
        new_vertices = [
            axes.coords_to_point(0, 0),
            axes.coords_to_point(A[0,0], A[1,0]),  # Transform of (1,0)
            axes.coords_to_point(A[0,0] + A[0,1], A[1,0] + A[1,1]),  # Transform of (1,1)
            axes.coords_to_point(A[0,1], A[1,1])   # Transform of (0,1)
        ]
        
        new_parallelogram = Polygon(
            *new_vertices,
            fill_opacity=0.3,
            fill_color=YELLOW,
            stroke_color=YELLOW,
            stroke_width=3
        )
        
        # New basis vectors
        new_u_arrow = Arrow(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(A[0,0], A[1,0]),
            color=RED,
            buff=0,
            stroke_width=4
        )
        new_v_arrow = Arrow(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(A[0,1], A[1,1]),
            color=GREEN,
            buff=0,
            stroke_width=4
        )
        
        # New labels
        new_u_label = MathTex(r"A\vec{u}", color=RED).next_to(new_u_arrow.get_end(), DOWN)
        new_v_label = MathTex(r"A\vec{v}", color=GREEN).next_to(new_v_arrow.get_end(), LEFT)
        
        # Animate transformation
        self.play(
            Transform(parallelogram, new_parallelogram),
            Transform(u_arrow, new_u_arrow),
            Transform(v_arrow, new_v_arrow),
            Transform(u_label, new_u_label),
            Transform(v_label, new_v_label),
            det_tracker.animate.set_value(abs(det_A)),
            run_time=3
        )
        
        self.wait(2)
        
        # Highlight the area change
        area_highlight = Text(
            f"Area scaled by factor of {abs(det_A):.2f}",
            font_size=24,
            color=YELLOW
        ).next_to(det_label, DOWN, buff=0.3)
        
        self.play(Write(area_highlight))
        self.wait(2)
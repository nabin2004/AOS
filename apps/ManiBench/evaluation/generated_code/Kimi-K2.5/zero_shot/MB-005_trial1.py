from manim import *
import numpy as np

class DeterminantGeometricInterpretation(Scene):
    def construct(self):
        # Setup coordinate plane
        plane = NumberPlane(
            x_range=[-1, 5, 1],
            y_range=[-1, 5, 1],
            background_line_style={
                "stroke_color": GREY,
                "stroke_width": 1,
                "stroke_opacity": 0.5
            }
        )
        self.add(plane)
        
        # Target matrix: [[2, 1], [1, 3]] with determinant 5
        target_matrix = np.array([[2.0, 1.0], [1.0, 3.0]])
        target_det = np.linalg.det(target_matrix)
        
        # ValueTracker for interpolation (0 = identity, 1 = target)
        alpha = ValueTracker(0.0)
        
        # Function to get current interpolated matrix
        def get_current_matrix():
            identity = np.eye(2)
            return identity * (1 - alpha.get_value()) + target_matrix * alpha.get_value()
        
        # Function to get current column vectors (u and v)
        def get_u():
            mat = get_current_matrix()
            return np.array([mat[0, 0], mat[1, 0], 0])
        
        def get_v():
            mat = get_current_matrix()
            return np.array([mat[0, 1], mat[1, 1], 0])
        
        # Create parallelogram with updaters
        parallelogram = Polygon(
            ORIGIN, get_u(), get_u() + get_v(), get_v(),
            fill_color=BLUE,
            fill_opacity=0.5,
            stroke_color=BLUE_E,
            stroke_width=3
        )
        
        def update_parallelogram(mob):
            u_vec = get_u()
            v_vec = get_v()
            mob.set_points_as_corners([ORIGIN, u_vec, u_vec + v_vec, v_vec, ORIGIN])
        
        parallelogram.add_updater(update_parallelogram)
        
        # Vector labels
        u_label = MathTex(r"\mathbf{u}", color=BLUE)
        u_label.add_updater(lambda m: m.next_to(get_u(), DR, buff=0.1))
        
        v_label = MathTex(r"\mathbf{v}", color=BLUE)
        v_label.add_updater(lambda m: m.next_to(get_v(), UL, buff=0.1))
        
        # Area labels
        original_area_label = MathTex(r"\text{Original Area} = 1").to_corner(UL)
        new_area_label = MathTex(
            rf"\text{{New Area}} = |\det(A)| = {abs(target_det):.0f}"
        ).to_corner(UL)
        
        # Matrix display
        matrix_tex = MathTex(
            r"A = \begin{bmatrix} 2 & 1 \\ 1 & 3 \end{bmatrix}"
        ).to_corner(UR)
        
        # Determinant display with continuous updating
        det_tracker = ValueTracker(1.0)
        det_decimal = DecimalNumber(1.0, num_decimal_places=2, color=YELLOW)
        det_label = VGroup(
            MathTex(r"\det(A) = "),
            det_decimal
        ).arrange(RIGHT)
        det_label.next_to(matrix_tex, DOWN)
        
        # Updater for determinant value calculation
        def update_det_tracker(obj):
            mat = get_current_matrix()
            det_val = np.linalg.det(mat)
            det_tracker.set_value(det_val)
        
        # Attach updater to parallelogram so it updates each frame
        parallelogram.add_updater(update_det_tracker)
        det_decimal.add_updater(lambda d: d.set_value(det_tracker.get_value()))
        
        # Initial scene setup
        self.play(
            Create(parallelogram),
            Write(u_label),
            Write(v_label),
            Write(original_area_label),
            Write(matrix_tex),
            Write(det_label),
            run_time=1
        )
        
        # Animate the transformation
        self.play(
            alpha.animate.set_value(1.0),
            Transform(original_area_label, new_area_label),
            run_time=4,
            rate_func=smooth
        )
        
        # Emphasize final determinant value
        self.play(
            det_decimal.animate.scale(1.3).set_color(GREEN),
            run_time=0.5
        )
        
        self.wait(2)
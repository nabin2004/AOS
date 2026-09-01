from manim import *
import numpy as np

class DeterminantAnimation(Scene):
    def construct(self):
        # Target matrix
        A_target = np.array([[1.5, 0.5], [0.5, 1.5]])
        
        # ValueTracker for interpolation
        t_tracker = ValueTracker(0)
        
        # Function to get interpolated matrix
        def get_matrix(t):
            return (1 - t) * np.eye(2) + t * A_target
        
        # Function to get 3x3 transformation matrix
        def get_matrix_3x3(t):
            M = get_matrix(t)
            return np.array([
                [M[0,0], M[0,1], 0],
                [M[1,0], M[1,1], 0],
                [0, 0, 1]
            ])
        
        # Original parallelogram points (unit square)
        original_points = [ORIGIN, RIGHT, RIGHT+UP, UP, ORIGIN]
        parallelogram = Polygon(*original_points, color=BLUE, fill_opacity=0.5)
        
        # Updater for parallelogram transformation
        parallelogram.add_updater(lambda m: m.set_points_as_corners([
            np.dot(get_matrix_3x3(t_tracker.get_value()), p) for p in original_points
        ]))
        
        # Labels
        original_label = Tex("Original Area = 1", font_size=24).to_edge(UP)
        new_label = Tex("New Area = ", font_size=24).to_edge(DOWN)
        det_decimal = DecimalNumber(1.0, num_decimal_places=2)
        det_decimal.add_updater(lambda d: d.set_value(
            abs(np.linalg.det(get_matrix(t_tracker.get_value())))
        ))
        new_area_group = VGroup(new_label, det_decimal).arrange(RIGHT).to_edge(DOWN)
        
        # Matrix display
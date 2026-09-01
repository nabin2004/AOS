from manim import *
import numpy as np

class DeterminantGeometricInterpretation(Scene):
    def construct(self):
        # Define the transformation matrix A
        # We will animate from Identity to this matrix
        final_matrix = np.array([[2, 1], [-1, 2]])
        det_value = np.linalg.det(final_matrix)
        
        # 1. Create the initial basis vectors (u, v) for the unit square
        # u = [1, 0], v = [0, 1]
        u_start = np.array([1, 0, 0])
        v_start = np.array([0, 1, 0])
        
        # Define the parallelogram (unit square initially)
        # Points: Origin, u, u+v, v
        poly_start = Polygon(
            [0, 0, 0],
            u_start[:2],
            (u_start + v_start)[:2],
            v_start[:2],
            color=BLUE,
            fill_opacity=0.5,
            stroke_width=2
        )
        
        # Basis vectors arrows
        arrow_u_start = Arrow(ORIGIN, u_start, color=RED, buff=0)
        arrow_v_start = Arrow(ORIGIN, v_start, color=GREEN, buff=0)
        
        # Labels for basis vectors
        label_u = Text("u", color=RED).next_to(arrow_u_start, RIGHT, small_buff=0.1)
        label_v = Text("v", color=GREEN).next_to(arrow_v_start, UP, small_buff=0.1)
        
        # Group initial geometry
        initial_geo = VGroup(poly_start, arrow_u_start, arrow_v_start, label_u, label_v)
        
        # 2. Display the Matrix
        matrix_tex = Matrix(final_matrix, left_bracket="[", right_bracket="]")
        matrix_tex.scale(0.8)
        matrix_tex.to_edge(UP).shift(RIGHT * 2)
        
        matrix_label = Text("Transformation Matrix A", font_size=24).next_to(matrix_tex, UP, small_buff=0.1)
        matrix_group = VGroup(matrix_label, matrix_tex)
        
        # 3. Area Labels
        original_area_label = Text("Original Area = 1", font_size=28)
        original_area_label.to_edge(LEFT).shift(UP * 2)
        
        new_area_label_template = Text("New Area = |det(A)|", font_size=28)
        new_area_label_template.to_edge(LEFT).shift(DOWN * 2)
        
        # Dynamic determinant value tracker
        det_tracker = ValueTracker(1.0)
        
        def get_det_text():
            val = det_tracker.get_value()
            # Format to avoid excessive decimals, handle negative zero etc
            formatted_val = f"{val:.2f}"
            return Text(f"New Area = |{formatted_val}|", font_size=28).move_to(new_area_label_template.get_center())

        new_area_label = always_redraw(get_det_text)
        
        # Add static parts to scene
        self.play(Write(original_area_label))
        self.play(Create(initial_geo))
        self.play(Write(matrix_group))
        self.play(Write(new_area_label))
        
        self.wait(1)
        
        # 4. Animation of the transformation
        # We need to interpolate the vectors from Identity to Matrix A
        
        def update_geometry(mob):
            t = det_tracker.get_value() # Reusing tracker as time proxy roughly, but let's use a separate alpha for smoothness if needed
            # Actually, let's just map the tracker directly to the interpolation factor for simplicity in this specific setup
            # But the tracker represents the determinant value? No, the prompt says "Show numerical value updating".
            # It's easier to animate a generic "alpha" from 0 to 1 and calculate the matrix and det at each step.
            pass

        # Let's restart the logic for the animation loop to be precise
        # We will remove the dynamic redraw for a moment and do a standard transform
        
        self.remove(new_area_label)
        
        def get_transformed_geometry(alpha):
            # Interpolate matrix from Identity to final_matrix
            current_mat = (1 - alpha) * np.eye(2) + alpha * final_matrix
            
            # Current basis vectors
            curr_u = np.array([current_mat[0][0], current_mat[1][0], 0])
            curr_v = np.array([current_mat[0][1], current_mat[1][1], 0])
            
            # Current determinant
            curr_det = np.linalg.det(current_mat)
            det_tracker.set_value(curr_det)
            
            # Create new polygon
            p_curr = Polygon(
                [0, 0, 0],
                curr_u[:2],
                (curr_u + curr_v)[:2],
                curr_v[:2],
                color=BLUE,
                fill_opacity=0.5,
                stroke_width=2
            )
            
            # Create new arrows
            arr_u = Arrow(ORIGIN, curr_u, color=RED, buff=0, stroke_width=2)
            arr_v = Arrow(ORIGIN, curr_v, color=GREEN, buff=0, stroke_width=2)
            
            # Labels need to move too
            lab_u = Text("u'", color=RED, font_size=24).next_to(arr_u, RIGHT, small_buff=0.05)
            lab_v = Text("v'", color=GREEN, font_size=24).next_to(arr_v, UP, small_buff=0.05)
            
            return VGroup(p_curr, arr_u, arr_v, lab_u, lab_v)

        # Initial draw at alpha=0 is already there, but let's make it smooth
        # We will replace the static group with an updating group
        
        geo_group = VGroup() # Placeholder
        
        def update_geo_func(mob, alpha):
            # This updater isn't standard for ValueTracker driven animation easily without a specific trick
            # Instead, we use self.play with an updater on the ValueTracker
            pass

        # Better approach: Use a ValueTracker for 'alpha' and update everything based on it
        alpha_tracker = ValueTracker(0)
        
        # Create a mobject that holds the geometry and updates based on alpha_tracker
        dynamic_geo = VGroup()
        
        def update_dynamic_geo(mob):
            alpha = alpha_tracker.get_value()
            current_mat = (1 - alpha) * np.eye(2) + alpha * final_matrix
            
            curr_u = np.array([current_mat[0][0], current_mat[1][0], 0])
            curr_v = np.array([current_mat[0][1], current_mat[1][1], 0])
            
            curr_det = np.linalg.det(current_mat)
            det_tracker.set_value(curr_det)
            
            p_curr = Polygon(
                [0, 0, 0],
                curr_u[:2],
                (curr_u + curr_v)[:2],
                curr_v[:2],
                color=BLUE,
                fill_opacity=0.5,
                stroke_width=2
            )
            
            arr_u = Arrow(ORIGIN, curr_u, color=RED, buff=0, stroke_width=2)
            arr_v = Arrow(ORIGIN, curr_v, color=GREEN, buff=0, stroke_width=2)
            
            # Adjust label positions slightly to avoid overlap during extreme squashing if any
            lab_u = Text("u", color=RED, font_size=24).next_to(arr_u, RIGHT, small_buff=0.05)
            lab_v = Text("v", color=GREEN, font_size=24).next_to(arr_v, UP, small_buff=0.05)
            
            mob.become(VGroup(p_curr, arr_u, arr_v, lab_u, lab_v))

        dynamic_geo.add_updater(update_dynamic_geo)
        
        # Replace initial static geometry with dynamic one
        self.remove(initial_geo)
        self.add(dynamic_geo)
        
        # Add the dynamic area label back
        self.add(new_area_label)
        
        # Animate the tracker
        self.play(alpha_tracker.animate.set_value(1), run_time=3, rate_func=smooth)
        
        self.wait(2)
        
        # Final cleanup of updaters to freeze the state
        dynamic_geo.clear_updaters()
        new_area_label.clear_updaters()
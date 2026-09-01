from manim import *
import numpy as np

class GradientDescent3D(ThreeDScene):
    def construct(self):
        # Set camera orientation
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)
        
        # Define loss function L(w1, w2) = w1^2 + w2^2
        def loss_func(u, v):
            return u**2 + v**2
            
        # Create 3D axes
        axes = ThreeDAxes(
            x_range=[-3.5, 3.5, 1],
            y_range=[-3.5, 3.5, 1],
            z_range=[0, 25, 5],
            x_length=7,
            y_length=7,
            z_length=5
        )
        axes_labels = axes.get_axis_labels(
            Tex("$w_1$").scale(0.7),
            Tex("$w_2$").scale(0.7),
            Tex("Loss").scale(0.7)
        )
        
        # Create loss surface
        surface = ParametricSurface(
            lambda u, v: axes.c2p(u, v, loss_func(u, v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(30, 30),
            fill_opacity=0.5,
            checkerboard_colors=[BLUE_D, BLUE_E]
        )
        
        # Create starting dot at (3, 3, 18)
        dot = Sphere(radius=0.1, color=RED).move_to(axes.c2p(3, 3, loss_func(3, 3)))
        
        # Create trajectory path (will be built during animation)
        trajectory = VMobject(color=GREEN)
        trajectory.set_points_as_corners([dot.get_center(), dot.get_center()])
        
        # Create 2D loss curve axes (fixed in frame)
        loss_axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 20, 5],
            x_length=4,
            y_length=3,
            axis_config={"include_numbers": True}
        ).to_corner(UL)
        loss_axes_labels = loss_axes.get_axis_labels("Step", "Loss")
        
        # Initialize loss curve
        loss_points = [(0, loss_func(3, 3))]  # (step, loss_value)
        loss_curve = VMobject(color=YELLOW)
        loss_curve.set_points_as_corners([
            loss_axes.c2p(x, y) for x, y in loss_points
        ])
        
        # Add fixed elements (2D graph)
        self.add_fixed_in_frame_mobjects(loss_axes, loss_axes_labels, loss_curve)
        
        # Add 3D
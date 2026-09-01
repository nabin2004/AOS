from manim import *
import numpy as np

class GradientDescent3D(Scene):
    def construct(self):
        # Configuration
        num_steps = 8
        learning_rate = 0.4
        decay = 0.8
        
        # Define the loss function L(w1, w2) = (w1^2 + w2^2) * some factor to make it visible
        # We use a simple convex function: L = 0.5 * (w1^2 + 2*w2^2) to show elliptical contours
        def loss_func(w1, w2):
            return 0.5 * (w1**2 + 2 * w2**2)

        def gradient_func(w1, w2):
            dw1 = w1
            dw2 = 2 * w2
            return np.array([dw1, dw2])

        # Initial position (high loss)
        start_pos = np.array([3.0, 2.0, 0.0])
        
        # Create Axes
        axes = ThreeDAxes(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            z_range=[0, 10, 1],
            x_length=6,
            y_length=6,
            z_length=4,
            axis_config={"include_tip": True, "include_numbers": False},
        )
        
        labels = axes.get_axis_labels(
            x_label="w_1", y_label="w_2", z_label="Loss"
        )
        
        # Create Surface
        surface = axes.plot_surface(
            lambda x, y: loss_func(x, y),
            x_range=[-4, 4, 0.2],
            y_range=[-4, 4, 0.2],
            fill_opacity=0.7,
            checkerboard_colors=[BLUE_D, BLUE_E],
            stroke_color=BLUE_B,
            stroke_width=0.5
        )
        
        # Group surface and axes for camera movement
        graph_group = VGroup(axes, labels, surface)
        
        # Add to scene
        self.add(graph_group)
        self.move_camera(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.8)
        self.begin_ambient_camera_rotation(rate=0.15)

        # Initialize Dot
        dot = Dot3D(color=YELLOW, radius=0.15)
        dot.move_to(axes.c2p(start_pos[0], start_pos[1], loss_func(start_pos[0], start_pos[1])))
        self.add(dot)

        # Trace line for the path
        trace = VMobject(color=YELLOW, stroke_width=4)
        trace.set_points_as_corners([dot.get_center(), dot.get_center()])
        self.add(trace)

        # Loss Curve Setup (2D plot on screen)
        loss_axes = Axes(
            x_range=[0, num_steps, 1],
            y_range=[0, 10, 1],
            x_length=3,
            y_length=2,
            axis_config={"color": WHITE},
        ).to_corner(UR, buff=0.5)
        
        loss_axes_labels = loss_axes.get_axis_labels(x_label="Step", y_label="L")
        loss_axes_labels.scale(0.7)
        
        loss_curve = VMobject(color=RED, stroke_width=3)
        loss_curve_points = []
        
        loss_group = VGroup(loss_axes, loss_axes_labels, loss_curve)
        # Fix loss graph to screen so it doesn't rotate with the 3D scene
        loss_group.fix_in_frame() 
        self.add(loss_group)

        # Current Position variables
        curr_w1, curr_w2 = start_pos[0], start_pos[1]
        history_loss = [loss_func(curr_w1, curr_w2)]
        
        # Update initial loss curve point
        loss_curve_points.append(loss_axes.c2p(0, history_loss[0]))
        loss_curve.set_points_as_corners(loss_curve_points)

        self.wait(1)

        # Animation Loop
        for i in range(num_steps):
            # 1. Compute Gradient
            grad = gradient_func(curr_w1, curr_w2)
            grad_norm = np.linalg.norm(grad)
            
            if grad_norm == 0:
                break
                
            # Normalize for visualization arrow
            grad_dir = grad / grad_norm
            
            # 2. Create Gradient Arrow (Visual aid)
            # Arrow starts at dot, points in direction of gradient (uphill)
            # We visualize -gradient (downhill) as the movement, but show gradient vector too
            arrow_length = 1.0
            start_point_3d = dot.get_center()
            end_point_3d = start_point_3d + axes.c2p(grad_dir[0], grad_dir[1], 0) - axes.get_origin()
            # Scale vector components to axes coordinates properly
            # axes.c2p converts data coords to scene coords. 
            # We need a vector displacement.
            vec_displacement = axes.get_vector(grad_dir * arrow_length, color=RED)
            vec_displacement.shift(start_point_3d)
            
            label_grad = Text("∇L", color=RED, font_size=24).next_to(vec_displacement, UP, buff=0.1)
            label_grad.fix_in_frame() # Keep text readable if camera rotates
            
            self.play(Create(vec_displacement), Write(label_grad), run_time=0.5)
            
            # 3. Calculate Step
            lr = learning_rate * (decay ** i)
            next_w1 = curr_w1 - lr * grad[0]
            next_w2 = curr_w2 - lr * grad[1]
            next_loss = loss_func(next_w1, next_w2)
            
            # Target position in 3D space
            target_point = axes.c2p(next_w1, next_w2, next_loss)
            
            # 4. Animate Movement
            self.play(
                dot.animate.move_to(target_point),
                UpdateFromFunc(trace, lambda m: m.set_points_as_corners([*trace.get_points()[:-1], target_point])),
                run_time=1.0
            )
            
            # Remove gradient arrow
            self.play(FadeOut(vec_displacement), FadeOut(label_grad), run_time=0.2)
            
            # 5. Update Loss Curve
            history_loss.append(next_loss)
            loss_curve_points.append(loss_axes.c2p(i + 1, next_loss))
            
            self.play(
                UpdateFromFunc(loss_curve, lambda m: m.set_points_as_corners(loss_curve_points)),
                run_time=0.5
            )
            
            # Update current position
            curr_w1, curr_w2 = next_w1, next_w2

        self.stop_ambient_camera_rotation()
        self.move_camera(phi=70 * DEGREES, theta=-45 * DEGREES, run_time=1)
        self.wait(2)
from manim import *

class GradientDescent3D(ThreeDScene):
    def construct(self):
        # Set up 3D axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[0, 6, 1],
            x_length=6,
            y_length=6,
            z_length=4,
        )
        
        # Axis labels
        x_label = MathTex("w_1").next_to(axes.x_axis.get_end(), RIGHT)
        y_label = MathTex("w_2").next_to(axes.y_axis.get_end(), UP)
        z_label = MathTex("L").next_to(axes.z_axis.get_end(), RIGHT)
        
        # Loss surface: L(w1, w2) = 0.5 * (w1^2 + w2^2)
        surface = Surface(
            lambda u, v: axes.c2p(u, v, 0.5 * (u**2 + v**2)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(30, 30),
            fill_opacity=0.6,
            fill_color=BLUE,
            stroke_color=BLUE_D,
            stroke_width=0.5,
        )
        
        # Gradient descent parameters
        w1, w2 = 2.0, 2.5
        learning_rate = 0.5
        decay = 0.8
        num_steps = 8
        
        def compute_loss(a, b):
            return 0.5 * (a**2 + b**2)
        
        # Initial point on surface
        z_val = compute_loss(w1, w2)
        dot = Sphere(radius=0.12, color=RED).move_to(axes.c2p(w1, w2, z_val))
        
        # 2D Loss history plot (upper right corner)
        loss_axes = Axes(
            x_range=[0, num_steps + 1, 1],
            y_range=[0, 6, 1],
            x_length=3.5,
            y_length=2.5,
            axis_config={"include_tip": False},
        ).to_corner(UR).shift(LEFT * 0.3)
        
        loss_title = Text("Loss", font_size=22).next_to(loss_axes, UP)
        step_label = MathTex("Step", font_size=18).next_to(loss_axes.x_axis, DOWN)
        loss_label = MathTex("L", font_size=18).next_to(loss_axes.y_axis, LEFT)
        
        # Initial scene setup
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)
        self.play(
            Create(axes),
            Write(x_label),
            Write(y_label),
            Write(z_label),
            run_time=2
        )
        self.play(Create(surface), run_time=2)
        self.play(Create(dot), run_time=1)
        self.play(
            Create(loss_axes),
            Write(loss_title),
            Write(step_label),
            Write(loss_label),
            run_time=1
        )
        
        # Track loss curve points
        prev_loss_point = None
        path_lines = VGroup()
        
        # Gradient descent animation
        for step in range(num_steps):
            # Compute gradient: ∇L = [w1, w2]
            grad_w1 = w1
            grad_w2 = w2
            
            # Current position
            current_z = compute_loss(w1, w2)
            current_pos = axes.c2p(w1, w2, current_z)
            
            # Next position (gradient step)
            w1_next = w1 - learning_rate * grad_w1
            w2_next = w2 - learning_rate * grad_w2
            next_z = compute_loss(w1_next, w2_next)
            next_pos = axes.c2p(w1_next, w2_next, next_z)
            
            # Gradient arrow (green, showing direction of steepest ascent)
            grad_scale = 0.4
            grad_end = axes.c2p(
                w1 + grad_scale * grad_w1, 
                w2 + grad_scale * grad_w2,
                current_z + grad_scale * (grad_w1**2 + grad_w2**2) / (2 * np.sqrt(grad_w1**2 + grad_w2**2) + 0.001)
            )
            grad_arrow = Arrow3D(
                start=current_pos,
                end=grad_end,
                color=GREEN,
                thickness=0.015,
            )
            
            # Step arrow (yellow, showing actual update direction)
            step_arrow = Arrow3D(
                start=current_pos,
                end=next_pos,
                color=YELLOW,
                thickness=0.02,
            )
            
            # Animate gradient and step
            self.play(Create(grad_arrow), run_time=0.4)
            self.play(Create(step_arrow), run_time=0.4)
            
            # Move dot to new position
            self.play(dot.animate.move_to(next_pos), run_time=0.8)
            
            # Draw path on surface
            path_line = Line(current_pos, next_pos, color=YELLOW, stroke_width=3)
            path_lines.add(path_line)
            self.add(path_line)
            
            # Update loss curve
            loss_point = Dot(loss_axes.c2p(step + 1, next_z), color=RED, radius=0.06)
            if prev_loss_point is not None:
                connector = Line(
                    prev_loss_point.get_center(),
                    loss_point.get_center(),
                    color=RED,
                    stroke_width=2
                )
                self.play(Create(connector), Create(loss_point), run_time=0.4)
            else:
                self.play(Create(loss_point), run_time=0.4)
            prev_loss_point = loss_point
            
            # Fade out arrows
            self.play(FadeOut(grad_arrow), FadeOut(step_arrow), run_time=0.3)
            
            # Update parameters for next iteration
            w1, w2 = w1_next, w2_next
            learning_rate *= decay
        
        # Final pause
        self.wait(2)
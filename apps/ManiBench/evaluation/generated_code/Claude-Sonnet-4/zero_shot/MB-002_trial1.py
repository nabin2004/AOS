from manim import *
import numpy as np

class GradientDescentVisualization(ThreeDScene):
    def construct(self):
        # Set up 3D scene
        self.set_camera_orientation(phi=60 * DEGREES, theta=45 * DEGREES)
        
        # Define loss function: L(w1, w2) = (w1-1)^2 + 2*(w2+0.5)^2 + 0.5
        def loss_function(w1, w2):
            return (w1 - 1)**2 + 2*(w2 + 0.5)**2 + 0.5
        
        # Define gradient function
        def gradient(w1, w2):
            dw1 = 2*(w1 - 1)
            dw2 = 4*(w2 + 0.5)
            return np.array([dw1, dw2])
        
        # Create parametric surface
        surface = Surface(
            lambda u, v: np.array([u, v, loss_function(u, v)]),
            u_range=[-2, 4],
            v_range=[-3, 2],
            resolution=(20, 20),
            fill_opacity=0.7,
            stroke_width=0.5
        )
        surface.set_fill_by_value(axes=self.camera.frame, colors=[BLUE, GREEN, YELLOW, RED])
        
        # Create axes
        axes = ThreeDAxes(
            x_range=[-2, 4, 1],
            y_range=[-3, 2, 1],
            z_range=[0, 8, 2],
            x_length=6,
            y_length=5,
            z_length=4
        )
        
        # Add axis labels
        x_label = axes.get_x_axis_label(Tex("w₁"))
        y_label = axes.get_y_axis_label(Tex("w₂"))
        z_label = axes.get_z_axis_label(Tex("Loss"))
        
        # Add surface and axes to scene
        self.add(axes, surface, x_label, y_label, z_label)
        self.wait(1)
        
        # Starting position
        w1, w2 = 3.5, 1.5
        loss_history = [loss_function(w1, w2)]
        
        # Create starting dot
        dot_3d = Dot3D(point=axes.c2p(w1, w2, loss_function(w1, w2)), color=RED, radius=0.1)
        self.add(dot_3d)
        
        # Create 2D loss curve in corner
        loss_axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 15, 5],
            x_length=3,
            y_length=2,
            tips=False
        ).scale(0.5).to_corner(UR)
        
        loss_title = Text("Loss History", font_size=20).next_to(loss_axes, UP, buff=0.1)
        self.add_fixed_in_frame_mobjects(loss_axes, loss_title)
        
        # Gradient descent parameters
        learning_rate = 0.3
        num_steps = 8
        
        for step in range(num_steps):
            # Compute gradient
            grad = gradient(w1, w2)
            grad_norm = np.linalg.norm(grad)
            
            # Create gradient arrow
            if grad_norm > 0:
                arrow_start = axes.c2p(w1, w2, loss_function(w1, w2))
                # Scale arrow for visibility
                arrow_direction = grad / grad_norm * 0.5
                arrow_end = axes.c2p(w1 + arrow_direction[0], w2 + arrow_direction[1], 
                                   loss_function(w1, w2))
                
                gradient_arrow = Arrow3D(
                    start=arrow_start,
                    end=arrow_end,
                    color=YELLOW,
                    thickness=0.02
                )
                
                # Show gradient arrow
                self.play(Create(gradient_arrow))
                self.wait(0.5)
                
                # Update position (move in negative gradient direction)
                step_size = learning_rate * (0.8 ** step)  # Diminishing step size
                w1_new = w1 - step_size * grad[0]
                w2_new = w2 - step_size * grad[1]
                
                # Move dot to new position
                new_position = axes.c2p(w1_new, w2_new, loss_function(w1_new, w2_new))
                self.play(
                    dot_3d.animate.move_to(new_position),
                    FadeOut(gradient_arrow),
                    run_time=1
                )
                
                # Update position
                w1, w2 = w1_new, w2_new
                loss_history.append(loss_function(w1, w2))
                
                # Update loss curve
                if len(loss_history) > 1:
                    loss_points = [
                        loss_axes.c2p(i, loss_history[i]) 
                        for i in range(len(loss_history))
                    ]
                    loss_curve = VMobject()
                    loss_curve.set_points_as_corners(loss_points)
                    loss_curve.set_stroke(WHITE, width=2)
                    
                    # Add dots for each point
                    loss_dots = VGroup(*[
                        Dot(point, radius=0.03, color=WHITE) 
                        for point in loss_points
                    ])
                    
                    if step == 0:
                        self.add_fixed_in_frame_mobjects(loss_curve, loss_dots)
                    else:
                        # Update existing curve
                        old_curve = self.mobjects[-2] if hasattr(self, '_loss_curve') else None
                        old_dots = self.mobjects[-1] if hasattr(self, '_loss_dots') else None
                        
                        if old_curve and old_dots:
                            self.remove(old_curve, old_dots)
                        
                        self.add_fixed_in_frame_mobjects(loss_curve, loss_dots)
                    
                    self._loss_curve = loss_curve
                    self._loss_dots = loss_dots
                
                self.wait(0.5)
        
        # Final pause
        self.wait(2)
        
        # Add final text showing convergence
        final_loss = loss_function(w1, w2)
        convergence_text = Text(
            f"Converged!\nFinal Loss: {final_loss:.2f}\nw₁: {w1:.2f}, w₂: {w2:.2f}",
            font_size=24
        ).to_corner(UL)
        
        self.add_fixed_in_frame_mobjects(convergence_text)
        self.play(Write(convergence_text))
        self.wait(3)
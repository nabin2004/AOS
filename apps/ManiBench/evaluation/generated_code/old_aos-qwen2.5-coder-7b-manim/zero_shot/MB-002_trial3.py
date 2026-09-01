from manim import *

class GradientDescentScene(Scene):
    def construct(self):
        # Create axes
        axes = Axes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            axis_config={"color": BLUE},
        )
        axes_labels = axes.get_axis_labels(x_label="w₁", y_label="w₂")
        
        # Define loss function
        def loss_func(x, y):
            return np.exp(-(x**2 + y**2))
        
        # Create loss surface
        surface = Surface(
            lambda u, v: [u, v, loss_func(u, v)],
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(50, 50),
            checkerboard_colors=[BLUE_D, BLUE_E],
        )
        surface.set_fill(opacity=0.7)
        
        # Add labels and surface to scene
        self.play(Create(axes), Write(axes_labels))
        self.play(Create(surface))
        self.wait()
        
        # Initial point
        initial_point = Dot(point=[1, 1, 0], color=YELLOW)
        self.play(FadeIn(initial_point))
        
        # Loss history
        loss_history = VGroup()
        
        # Gradient descent steps
        for i in range(5):
            # Compute gradient
            grad_x = -2 * initial_point.get_center()[0] * np.exp(-(initial_point.get_center()[0]**2 + initial_point.get_center()[1]**2))
            grad_y = -2 * initial_point.get_center()[1] * np.exp(-(initial_point.get_center()[0]**2 + initial_point.get_center()[1]**2))
            
            # Move dot in direction of -grad
            new_point = Dot(point=[initial_point.get_center()[0] - 0.1*grad_x, initial_point.get_center()[1] - 0.1*grad_y, 0], color=YELLOW)
            
            # Update loss history
            current_loss = Text(f"Loss: {loss_func(new_point.get_center()[0], new_point.get_center()[1]):.2f}", font_size=24)
            current_loss.next_to(axes, DOWN)
            loss_history.add(current_loss)
            
            # Draw arrow indicating gradient direction
            arrow = Arrow(
                start=initial_point,
                end=new_point,
                buff=0,
                color=RED,
                max_tip_length_to_length_ratio=0.2,
            )
            
            # Animate movement
            self.play(
                TransformFromCopy(initial_point, new_point),
                FadeOut(arrow),
                run_time=0.5
            )
            self.play(FadeIn(arrow))
            self.play(TransformFromCopy(arrow, Text("Gradient", font_size=24).next_to(arrow, UP)))
            self.play(FadeOut(arrow))
            
            # Update text
            if i == 0:
                self.play(Write(current_loss))
            else:
                self.play(Transform(loss_history[-1], current_loss))
            
            # Update initial point
            initial_point = new_point
            
            # Wait briefly
            self.wait(0.5)
        
        # Final label
        final_text = Text("Converged!", font_size=36).to_edge(DOWN)
        self.play(Write(final_text))
        self.wait(2)
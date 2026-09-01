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
        ).set_fill(opacity=0.7)
        
        # Add labels and surface to scene
        self.play(Create(axes), Write(axes_labels))
        self.play(Create(surface))
        self.wait()
        
        # Initial point
        initial_point = Dot(point=[0, 0, 0], color=YELLOW)
        self.play(FadeIn(initial_point))
        
        # Loss history
        loss_history = VGroup()
        
        # Gradient descent parameters
        learning_rate = 0.1
        num_steps = 8
        
        for i in range(num_steps):
            # Get current coordinates
            x, y = initial_point.get_center()[:2]
            
            # Compute gradient
            grad_x = -2 * x * np.exp(-(x**2 + y**2))
            grad_y = -2 * y * np.exp(-(x**2 + y**2))
            
            # Update point position
            new_x = x - learning_rate * grad_x
            new_y = y - learning_rate * grad_y
            
            # Move point
            self.play(
                initial_point.animate.move_to([new_x, new_y, 0]),
                run_time=0.5,
            )
            
            # Draw arrow showing gradient direction
            arrow = Arrow(
                start=initial_point.get_center(),
                end=[new_x, new_y, 0] + [-grad_x, -grad_y, 0] * 0.5,
                buff=0,
                color=RED,
            )
            self.play(GrowArrow(arrow))
            self.remove(arrow)
            
            # Update loss history
            new_loss = loss_func(new_x, new_y)
            loss_dot = Dot(point=[new_x, new_y, new_loss], color=GREEN)
            loss_line = Line(
                start=[new_x, new_y, 0],
                end=[new_x, new_y, new_loss],
                color=GREEN,
            )
            loss_history.add(loss_dot, loss_line)
            
            # Reduce learning rate for next step
            if i < num_steps - 1:
                learning_rate *= 0.9
            
            self.wait(0.2)
        
        # Final label
        final_text = Text("Gradient Descent", font_size=24).to_edge(UP)
        self.play(Write(final_text))
        self.wait(2)
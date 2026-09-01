from manim import *

class GradientDescent3D(ThreeDScene):
    def construct(self):
        # Set up 3D axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[0, 6, 1],
            axis_config={"color": BLUE}
        )
        labels = axes.get_axis_labels(
            Tex("$w_1$"), Tex("$w_2$"), Tex("Loss")
        )

        # Define the loss function: L(w1, w2) = w1^2 + 0.5*w2^2 + w1*w2 + 2
        def loss_function(u, v):
            return u**2 + 0.5*v**2 + u*v + 2

        # Create parametric surface
        surface = ParametricSurface(
            lambda u, v: axes.c2p(u, v, loss_function(u, v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=64,
            fill_opacity=0.7,
            checkerboard_colors=[YELLOW_D, YELLOW_E],
            stroke_color=WHITE,
            stroke_width=0.5
        )

        # Add title
        title = Title("Gradient Descent on 2D Loss Landscape", font_size=36)

        # Set camera orientation
        self.set_camera_orientation(phi=60*DEGREES, theta=45*DEGREES)

        # Add axes, labels, surface, and title
        self.add(axes, labels, surface, title)

        # Gradient of the loss function: ∇L = [2w1 + w2, w2 + w1]
        def gradient(w1, w2):
            dw1 = 2*w1 + w2
            dw2 = w2 + w1
            return np.array([dw1, dw2])

        # Initial point (high loss)
        w1, w2 = -2.5, 2.0
        current_point = np.array([w1, w2])
        
        # Dot on the surface
        dot = Dot3D(point=axes.c2p(w1, w2, loss_function(w1, w2)), color=RED, radius=0.08)
        self.add(dot)

        # Loss curve (2D plot in corner)
        loss_graph = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 10, 2],
            x_length=3,
            y_length=2,
            axis_config={"color": WHITE}
        ).to_corner(UL)
        loss_graph_labels = loss_graph.get_axis_labels("Step", "Loss")
        loss_plot = VGroup(loss_graph, loss_graph_labels)
        self.add(loss_plot)

        # Line graph for loss history
        loss_values = [loss_function(w1, w2)]
        loss_line = loss_graph.plot_line_graph(
            x_values=[0],
            y_values=[loss_values[0]],
            line_color=YELLOW,
            add_vertex_dots=True,
            vertex_dot_style={'fill_color': YELLOW, 'radius': 0.05}
        )
        self.add(loss_line)

        # Store path for animation
        path = VMobject(stroke_color=RED, stroke_width=4)
        path.set_points_as_corners([dot.get_center(), dot.get_center()])

        # Gradient arrow
        grad_vec = gradient(w1, w2)
        grad_norm = np.linalg.norm(grad_vec)
        if grad_norm > 0:
            arrow_scale = 0.5
            grad_arrow = Arrow3D(
                start=axes.c2p(w1, w2, loss_function(w1, w2)),
                end=axes.c2p(w1 + arrow_scale * grad_vec[0], w2 + arrow_scale * grad_vec[1], 
                           loss_function(w1, w2)),
                color=GREEN
            )
        else:
            grad_arrow = Arrow3D(
                start=axes.c2p(w1, w2, loss_function(w1, w2)),
                end=axes.c2p(w1, w2, loss_function(w1, w2) + 0.1),
                color=GREEN
            )
        self.add(grad_arrow)

        # Gradient label
        grad_label = Text("∇L", font_size=20, color=GREEN).next_to(grad_arrow, RIGHT)
        self.add(grad_label)

        # Step counter
        step_text = Text("Step 0", font_size=24).to_corner(DR)
        self.add(step_text)

        # Perform gradient descent steps
        for step in range(1, 8):
            self.wait(0.5)
            
            # Compute gradient
            grad_vec = gradient(current_point[0], current_point[1])
            grad_norm = np.linalg.norm(grad_vec)
            
            # Adaptive step size (diminishing)
            step_size = 0.3 / (1 + 0.3 * step)
            
            # Update point
            new_point = current_point - step_size * grad_vec / (grad_norm + 1e-8)
            
            # Animate gradient arrow changing
            new_grad_vec = gradient(new_point[0], new_point[1])
            new_arrow_scale = 0.5
            new_grad_arrow = Arrow3D(
                start=axes.c2p(current_point[0], current_point[1], loss_function(current_point[0], current_point[1])),
                end=axes.c2p(current_point[0] + new_arrow_scale * grad_vec[0], 
                           current_point[1] + new_arrow_scale * grad_vec[1], 
                           loss_function(current_point[0], current_point[1])),
                color=GREEN
            )
            
            # Move dot
            new_dot = Dot3D(
                point=axes.c2p(new_point[0], new_point[1], loss_function(new_point[0], new_point[1])),
                color=RED, radius=0.08
            )
            
            # Update path
            new_path = path.copy()
            new_path.add_points_as_corners([new_dot.get_center()])
            
            # Update loss value and graph
            loss_val = loss_function(new_point[0], new_point[1])
            loss_values.append(loss_val)
            new_loss_line = loss_graph.plot_line_graph(
                x_values=list(range(len(loss_values))),
                y_values=loss_values,
                line_color=YELLOW,
                add_vertex_dots=True,
                vertex_dot_style={'fill_color': YELLOW, 'radius': 0.05}
            )
            
            # Update step counter
            new_step_text = Text(f"Step {step}", font_size=24).to_corner(DR)
            
            # Play animations
            self.play(
                Transform(grad_arrow, new_grad_arrow),
                Transform(grad_label, Text("∇L", font_size=20, color=GREEN).next_to(new_grad_arrow, RIGHT)),
                MoveAlongPath(dot, new_path),
                Transform(path, new_path),
                Transform(loss_line, new_loss_line),
                Transform(step_text, new_step_text),
                run_time=1.5
            )
            
            # Update current point
            current_point = new_point

        self.wait(2)
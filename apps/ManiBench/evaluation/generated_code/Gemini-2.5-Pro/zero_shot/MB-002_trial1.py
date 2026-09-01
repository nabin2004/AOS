from manim import *
import numpy as np

class GradientDescent2D(ThreeDScene):
    """
    An animation of gradient descent on a 2D loss landscape.
    """
    def construct(self):
        # 1. Set up the scene and camera
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES, zoom=0.75)
        
        # 2. Define the loss function and its gradient
        # L(w₁, w₂) = 0.1 * ((w₁ - 2)² + (w₂ - 1)²) + 0.5
        def loss_function(w1, w2):
            return 0.1 * ((w1 - 2)**2 + (w2 - 1)**2) + 0.5

        # ∇L = [∂L/∂w₁, ∂L/∂w₂] = [0.2 * (w₁ - 2), 0.2 * (w₂ - 1)]
        def gradient_function(w1, w2):
            return np.array([0.2 * (w1 - 2), 0.2 * (w2 - 1)])

        # 3. Create 3D axes and the loss surface
        axes = ThreeDAxes(
            x_range=[-4, 6, 2],
            y_range=[-4, 6, 2],
            z_range=[0, 5, 1],
            x_length=8,
            y_length=8,
            z_length=5,
        )
        
        axis_labels = axes.get_axis_labels(
            x_label=MathTex("w_1"), y_label=MathTex("w_2"), z_label=Tex("Loss")
        )
        
        surface = Surface(
            lambda u, v: axes.c2p(u, v, loss_function(u, v)),
            u_range=[-4, 6],
            v_range=[-4, 6],
            resolution=(42, 42),
            fill_opacity=0.7,
            checkerboard_colors=[BLUE_D, BLUE_E],
        )

        self.add(axes, surface, axis_labels)

        # 4. Set up the 2D loss history plot in the corner
        loss_axes = Axes(
            x_range=[0, 8, 2],
            y_range=[0, 4, 1],
            x_length=3.5,
            y_length=2.5,
            axis_config={"color": WHITE, "include_tip": False},
        ).to_corner(UR).add_background_rectangle(opacity=0.5, buff=0.1)

        loss_axis_labels = loss_axes.get_axis_labels(
            x_label=Tex("Step").scale(0.7), y_label=Tex("Loss").scale(0.7)
        )
        loss_plot_title = Text("Loss History").scale(0.5).next_to(loss_axes, UP, buff=0.1)
        
        self.add_fixed_in_frame(loss_axes, loss_axis_labels, loss_plot_title)

        # 5. Initialize Gradient Descent parameters and objects
        num_steps = 8
        learning_rate = 2.5
        w_current = np.array([-3.5, 3.0])
        
        dot = Dot3D(
            point=axes.c2p(w_current[0], w_current[1], loss_function(*w_current)),
            color=RED,
            radius=0.1
        )
        self.add(dot)

        # VGroups to hold the paths
        path_on_surface = VGroup()
        loss_history_coords = []
        loss_dots_vg = VGroup()
        loss_path_vg = VGroup()
        self.add_fixed_in_frame(loss_dots_vg, loss_path_vg)

        # Initial point on loss plot
        initial_loss = loss_function(*w_current)
        loss_history_coords.append(loss_axes.c2p(0, initial_loss))
        initial_loss_dot = Dot(loss_history_coords[0], color=RED, radius=0.05)
        loss_dots_vg.add(initial_loss_dot)

        self.wait(1)

        # 6. Animation loop for gradient descent steps
        for i in range(num_steps):
            # (a) Compute gradient and create arrow
            grad = gradient_function(*w_current)
            
            grad_arrow = Arrow(
                start=axes.c2p(w_current[0], w_current[1], 0),
                end=axes.c2p(w_current[0] - grad[0], w_current[1] - grad[1], 0),
                buff=0,
                color=YELLOW,
                stroke_width=5,
                max_tip_length
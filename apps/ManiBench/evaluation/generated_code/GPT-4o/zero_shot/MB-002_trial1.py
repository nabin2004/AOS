from manim import *
import numpy as np

class GradientDescent2D(ThreeDScene):
    def construct(self):
        # Define the loss function L(w1, w2)
        def loss_function(w1, w2):
            return w1**2 + w2**2 + 0.5 * np.sin(3 * w1) * np.cos(3 * w2)

        # Define the gradient of the loss function
        def gradient(w1, w2):
            grad_w1 = 2 * w1 + 1.5 * 3 * np.cos(3 * w1) * np.cos(3 * w2)
            grad_w2 = 2 * w2 - 1.5 * 3 * np.sin(3 * w1) * np.sin(3 * w2)
            return np.array([grad_w1, grad_w2])

        # Set up axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[0, 10, 2],
            x_length=7,
            y_length=7,
            z_length=5,
        )
        axes_labels = axes.get_axis_labels(x_label="w_1", y_label="w_2", z_label="Loss")

        # Create the parametric surface for the loss landscape
        surface = Surface(
            lambda u, v: axes.c2p(u, v, loss_function(u, v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(30, 30),
            fill_opacity=0.8,
            checkerboard_colors=[BLUE_D, BLUE_E],
        )

        # Add axes and surface to the scene
        self.set_camera_orientation(phi=75 * DEGREES, theta=45 * DEGREES)
        self.add(axes, axes_labels, surface)

        # Initialize the dot at a high-loss location
        dot_position = np.array([2.5, 2.5])  # Starting point (w1, w2)
        dot = Dot3D(point=axes.c2p(dot_position[0], dot_position[1], loss_function(*dot_position)), color=RED)
        self.add(dot)

        # Initialize the loss curve
        loss_values = [loss_function(*dot_position)]
        loss_curve = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 10, 2],
            x_length=5,
            y_length=3,
            axis_config={"include_numbers": True},
        ).to_corner(UL)
        loss_curve_labels = loss_curve.get_axis_labels(x_label="Step", y_label="Loss")
        loss_graph = VGroup(loss_curve, loss_curve_labels)
        self.add_fixed_in_frame_mobjects(loss_graph)

        # Plot the initial loss value
        loss_dot = Dot(loss_curve.c2p(0, loss_values[0]), color=RED)
        self.add_fixed_in_frame_mobjects(loss_dot)

        # Gradient descent parameters
        num_steps = 10
        step_size = 0.5

        # Perform gradient descent
        for step in range(1, num_steps + 1):
            # Compute gradient
            grad = gradient(*dot_position)

            # Compute new position
            new_position = dot_position - step_size * grad
            new_loss = loss_function(*new_position)

            # Create an arrow showing the gradient direction
            arrow = Arrow3D(
                start=axes.c2p(dot_position[0], dot_position[1], loss_function(*dot_position)),
                end=axes.c2p(new_position[0], new_position[1], loss_function(*new_position)),
                color=YELLOW,
                buff=0.1,
            )
            self.add(arrow)

            # Animate the dot moving to the new position
            self.play(
                MoveAlongPath(dot, Line(
                    axes.c2p(dot_position[0], dot_position[1], loss_function(*dot_position)),
                    axes.c2p(new_position[0], new_position[1], loss_function(*new_position))
                )),
                run_time=0.5
            )
            self.remove(arrow)

            # Update the loss curve
            loss_values.append(new_loss)
            new_loss_dot = Dot(loss_curve.c2p(step, new_loss), color=RED)
            self.play(Transform(loss_dot, new_loss_dot), run_time=0.5)

            # Update position and step size
            dot_position = new_position
            step_size *= 0.9  # Diminishing step size

        self.wait(2)
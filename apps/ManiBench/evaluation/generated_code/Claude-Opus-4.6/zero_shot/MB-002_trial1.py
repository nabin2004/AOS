from manim import *
import numpy as np


class GradientDescent(ThreeDScene):
    def construct(self):
        # Define the loss function and its gradient
        def loss_func(w1, w2):
            return 0.5 * w1**2 + w2**2 + 0.3 * np.sin(2 * w1) * np.cos(2 * w2)

        def grad_loss(w1, w2):
            dL_dw1 = w1 + 0.6 * np.cos(2 * w1) * np.cos(2 * w2)
            dL_dw2 = 2 * w2 - 0.6 * np.sin(2 * w1) * np.sin(2 * w2)
            return np.array([dL_dw1, dL_dw2])

        # Set up 3D axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[0, 6, 1],
            x_length=6,
            y_length=6,
            z_length=4,
            axis_config={"include_numbers": False},
        )

        # Labels
        w1_label = MathTex("w_1").scale(0.6)
        w2_label = MathTex("w_2").scale(0.6)
        loss_label = MathTex("\\text{Loss}").scale(0.6)

        w1_label.next_to(axes.x_axis.get_end(), RIGHT, buff=0.1)
        w2_label.next_to(axes.y_axis.get_end(), UP, buff=0.1)
        loss_label.next_to(axes.z_axis.get_end(), UP, buff=0.1)

        # Create the surface
        surface = Surface(
            lambda u, v: axes.c2p(u, v, loss_func(u, v)),
            u_range=[-2.8, 2.8],
            v_range=[-2.8, 2.8],
            resolution=(40, 40),
            fill_opacity=0.6,
        )
        surface.set_style(fill_opacity=0.6)
        surface.set_fill_by_value(
            axes=axes,
            colorscale=[(BLUE, 0), (GREEN, 2), (YELLOW, 4), (RED, 6)],
            axis=2,
        )

        # Set camera
        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)

        # Add axes and surface
        self.play(Create(axes), run_time=1)
        self.add_fixed_orientation_mobjects(w1_label, w2_label, loss_label)
        self.play(
            Write(w1_label),
            Write(w2_label),
            Write(loss_label),
            run_time=0.8,
        )
        self.play(Create(surface), run_time=2)
        self.wait(0.5)

        # Gradient descent parameters
        w = np.array([2.5, 2.0])
        initial_lr = 0.3
        num_steps = 8
        decay = 0.85

        # Create the initial dot on the surface
        z_val = loss_func(w[0], w[1])
        dot = Sphere(radius=0.08, color=RED).move_to(
            axes.c2p(w[0], w[1], z_val)
        )
        dot.set_color(RED)
        self.play(Create(dot), run_time=0.5)

        # Store loss history
        loss_history = [z_val]

        # Create a 2D loss curve panel in the corner
        # We'll use a fixed-orientation group
        loss_axes = Axes(
            x_range=[0, num_steps + 1, 1],
            y_range=[0, 7, 1],
            x_length=3,
            y_length=2,
            axis_config={"include_numbers": False, "tick_size": 0.05},
        ).scale(0.8)

        loss_axes_bg = Rectangle(
            width=3.0,
            height=2.2,
            fill_color=BLACK,
            fill_opacity=0.8,
            stroke_color=WHITE,
            stroke_width=1,
        )

        loss_title = Text("Loss Curve", font_size=16)
        step_label = Text("Step", font_size=12)
        loss_val_label = Text("Loss", font_size=12)

        # Position the panel
        panel = VGroup(loss_axes_bg, loss_axes, loss_title, step_label, loss_val_label)
        loss_axes_bg.move_to(ORIGIN)
        loss_axes.move_to(ORIGIN)
        loss_title.next_to(loss_axes, UP, buff=0.05)
        step_label.next_to(loss_axes.x_axis, DOWN, buff=0.05)
        loss_val_label.next_to(loss_axes.y_axis, LEFT, buff=0.05).rotate(90 * DEGREES)

        panel.to_corner(UR, buff=0.3)

        self.add_fixed_in_frame_mobjects(panel)
        self.play(FadeIn(panel), run_time=0.5)

        # Plot initial point on loss curve
        loss_dots = []
        loss_lines = []

        initial_loss_dot = Dot(
            loss_axes.c2p(0, loss_history[0]),
            color=YELLOW,
            radius=0.04,
        )
        loss_dots.append(initial_loss_dot)
        self.add_fixed_in_frame_mobjects(initial_loss_dot)
        self.play(Create(initial_loss_dot), run_time=0.3)

        # Gradient descent loop
        lr = initial_lr
        for step in range(num_steps):
            # Compute gradient
            g = grad_loss(w[0], w[1])
            g_norm = np.linalg.norm(g)

            # Create gradient arrow on the surface
            current_pos = axes.c2p(w[0], w[1], loss_func(w[0], w[1]))

            # Arrow direction: negative gradient projected onto the surface
            arrow_scale = min(0.8, 0.4 * g_norm)
            neg_g = -g / (g_norm + 1e-8)

            # Compute the 3D direction of the arrow on the surface
            w_next_arrow = w + neg_g * 0.5
            z_next_arrow = loss_func(w_next_arrow[0], w_next_arrow[1])
            arrow_end = axes.c2p(w_next_arrow[0], w_next_arrow[1], z_next_arrow)

            arrow = Arrow3D(
                start=current_pos,
                end=arrow_end,
                color=YELLOW,
                thickness=0.02,
                height=0.2,
            )

            self.play(Create(arrow), run_time=0.4)

            # Update weights
            w_new = w - lr * g
            # Clamp to range
            w_new = np.clip(w_new, -2.8, 2.8)
            z_new = loss_func(w_new[0], w_new[1])

            # Move dot
            new_pos = axes.c2p(w_new[0], w_new[1], z_new)
            self.play(dot.animate.move_to(new_pos), run_time=0.6)

            # Remove arrow
            self.play(FadeOut(arrow), run_time=0.2)

            # Update loss history
            loss_history.append(z_new)
            w = w_new
            lr *= decay

            # Add point to loss curve
            new_loss_dot = Dot(
                loss_axes.c2p(step + 1, z_new),
                color=YELLOW,
                radius=0.04,
            )
            new_loss_line = Line(
                loss_axes.c2p(step, loss_history[-2]),
                loss_axes.c2p(step + 1, z_new),
                color=YELLOW,
                stroke_width=2,
            )
            loss_dots.append(new_loss_dot)
            loss_lines.append(new_loss_line)

            self.add_fixed_in_frame_mobjects(new_loss_dot, new_loss_line)
            self.play(
                Create(new_loss_line),
                Create(new_loss_dot),
                run_time=0.3,
            )

        # Final display
        # Show final loss value
        final_loss_text = MathTex(
            f"L^* \\approx {loss_history[-1]:.3f}", color=GREEN
        ).scale(0.5)
        final_loss_text.next_to(loss_axes, DOWN, buff=0.3)
        self.add_fixed_in_frame_mobjects(final_loss_text)
        self.play(Write(final_loss_text), run_time=0.5)

        # Rotate camera to show the result
        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(4)
        self.stop_ambient_camera_rotation()
        self.wait(1)
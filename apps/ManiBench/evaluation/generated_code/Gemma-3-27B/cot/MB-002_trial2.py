from manim import *

class GradientDescent(ThreeDScene):
    def construct(self):
        # Define the loss function
        def loss_function(w1, w2):
            return (w1**2 + w2**2) + np.sin(w1 * 5) * np.cos(w2 * 5)

        # Create the surface
        surface = ParametricSurface(
            lambda u, v: (u, v, loss_function(u, v)),
            u_range=[-2, 2],
            v_range=[-2, 2],
            resolution=(50, 50)
        )
        surface.set_opacity(0.8)

        # Initial point
        initial_point = np.array([1.5, 1.5])
        dot = Dot3D(point=surface.point_from_parameterized(initial_point[0], initial_point[1]), color=YELLOW)
        dot.scale(0.05)

        # Loss curve
        axes = Axes(
            x_range=[0, 10],
            y_range=[0, 10],
            x_length=5,
            y_length=5,
            axis_config={"include_numbers": False}
        )
        axes.add_coordinate_labels(x_label="Iteration", y_label="Loss")
        loss_curve = axes.plot_line(lambda x: loss_function(initial_point[0] - x * 0.2, initial_point[1] - x * 0.2), x_range=[0, 10], color=BLUE)

        # Gradient descent parameters
        learning_rate = 0.2
        num_steps = 10

        # Gradient calculation
        def gradient(w1, w2):
            dw1 = 2 * w1 + 5 * np.cos(w1 * 5) * np.cos(w2 * 5)
            dw2 = 2 * w2 - 5 * np.sin(w1 * 5) * np.sin(w2 * 5)
            return np.array([dw1, dw2])

        # Animation
        self.play(Create(surface))
        self.play(Create(dot))

        for i in range(num_steps):
            # Calculate gradient
            grad = gradient(initial_point[0], initial_point[1])
            grad_arrow = Arrow3D(start=surface.point_from_parameterized(initial_point[0], initial_point[1]),
                                 end=surface.point_from_parameterized(initial_point[0], initial_point[1]) + 0.2 * -grad,
                                 color=RED, buff=0)

            # Update dot position
            initial_point -= learning_rate * grad
            dot.move_to(surface.point_from_parameterized(initial_point[0], initial_point[1]))

            # Update loss curve
            loss_value = loss_function(initial_point[0], initial_point[1])
            new_loss_curve = axes.plot_line(lambda x: loss_function(initial_point[0] - x * 0.2, initial_point[1] - x * 0.2), x_range=[0, i+1], color=BLUE)
            
            self.play(Create(grad_arrow), MoveToTarget(dot))
            self.play(Transform(loss_curve, new_loss_curve))
            self.remove(grad_arrow)
            learning_rate *= 0.9  # Diminish learning rate

        # Add labels
        w1_label = Tex("w₁").next_to(surface, UP + RIGHT)
        w2_label = Tex("w₂").next_to(surface, UP + LEFT)
        loss_label = Tex("Loss").next_to(surface, BACK)

        self.play(Write(w1_label), Write(w2_label), Write(loss_label))
        self.wait(2)
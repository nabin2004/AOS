from manim import *

class GradientDescent(Scene):
    def construct(self):
        # Define the loss landscape
        def loss_function(w1, w2):
            return (w1**2 + w2**2) + np.sin(w1 * 5) * np.cos(w2 * 5)

        # Create the parametric surface
        surface = ParametricSurface(
            lambda u, v: (u, v, loss_function(u, v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(50, 50)
        )
        surface.set_style(fill_opacity=0.8)

        # Initial point
        initial_w1 = 2.5
        initial_w2 = 2.5
        initial_point = [initial_w1, initial_w2, loss_function(initial_w1, initial_w2)]
        dot = Dot(initial_point, color=YELLOW)

        # Axes labels
        w1_label = Tex("w₁").next_to(surface, LEFT)
        w2_label = Tex("w₂").next_to(surface, BACK)
        loss_label = Tex("Loss").next_to(surface, UP)

        self.play(Create(surface), Write(w1_label), Write(w2_label), Write(loss_label))
        self.play(Create(dot))
        self.wait(2)

        # Loss curve
        loss_curve = NumberPlane(
            x_range=[0, 10],
            y_range=[0, 20],
            x_length=5,
            y_length=3
        )
        loss_curve_label_x = Tex("Iteration").next_to(loss_curve, X_AXIS)
        loss_curve_label_y = Tex("Loss").next_to(loss_curve, Y_AXIS)
        loss_values = []
        loss_curve_line = Line()

        loss_curve.add_coordinate_labels(x_range=[0, 10], y_range=[0, 20])

        self.play(Create(loss_curve), Write(loss_curve_label_x), Write(loss_curve_label_y))
        self.wait(1)

        # Gradient descent parameters
        learning_rate = 0.2
        num_steps = 8

        # Gradient calculation (approximate)
        def calculate_gradient(w1, w2):
            h = 0.001
            dw1 = (loss_function(w1 + h, w2) - loss_function(w1 - h, w2)) / (2 * h)
            dw2 = (loss_function(w1, w2 + h) - loss_function(w1, w2 - h)) / (2 * h)
            return dw1, dw2

        for i in range(num_steps):
            # Calculate gradient
            dw1, dw2 = calculate_gradient(initial_w1, initial_w2)

            # Gradient arrow
            gradient_arrow = Arrow(
                dot.get_center(),
                dot.get_center() + np.array([-dw1 * learning_rate, -dw2 * learning_rate, 0]),
                color=RED,
                buff=0.1
            )

            # Update position
            new_w1 = initial_w1 - dw1 * learning_rate
            new_w2 = initial_w2 - dw2 * learning_rate
            new_point = [new_w1, new_w2, loss_function(new_w1, new_w2)]

            # Update dot position
            dot.move_to(new_point)

            # Update loss curve
            loss_values.append(loss_function(new_w1, new_w2))
            if len(loss_values) > 1:
                new_line = Line(loss_curve.c2p(0, loss_values[0]), loss_curve.c2p(i + 1, loss_values[-1]), color=BLUE)
                self.play(Transform(loss_curve_line, new_line))

            # Display iteration number
            iteration_label = Tex(f"Iteration: {i+1}").to_corner(UR)

            # Display learning rate
            alpha_label = Tex(f"α = {learning_rate:.2f}").next_to(iteration_label, DOWN)

            self.play(
                Create(gradient_arrow),
                MoveToTarget(dot),
                Write(iteration_label),
                Write(alpha_label)
            )
            self.wait(0.5)

            # Reduce learning rate
            learning_rate *= 0.8

            self.play(Uncreate(gradient_arrow), Unwrite(iteration_label), Unwrite(alpha_label))

        self.wait(2)
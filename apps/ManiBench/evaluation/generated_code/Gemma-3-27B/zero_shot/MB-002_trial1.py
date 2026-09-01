from manim import *

class GradientDescent(Scene):
    def construct(self):
        # Define the loss function
        def loss_function(w1, w2):
            return (w1**2 + w2**2) + np.sin(w1 * 5) * np.cos(w2 * 5)

        # Create the surface
        w1_range = [-3, 3]
        w2_range = [-3, 3]
        surface = Surface(
            lambda w1, w2: loss_function(w1, w2),
            x_range=w1_range,
            y_range=w2_range,
            resolution=(50, 50),
            color=BLUE_E
        )
        surface.scale(0.75)
        self.play(Create(surface))

        # Initial point
        initial_w1 = 2.5
        initial_w2 = 2.5
        initial_point = Dot(surface.point_from_coordinates(initial_w1, initial_w2, loss_function(initial_w1, initial_w2)), color=RED)
        self.play(Create(initial_point))

        # Loss curve
        loss_curve = Line()
        loss_history = []

        # Gradient descent parameters
        learning_rate = 0.2
        num_steps = 8

        # Gradient function (numerical approximation)
        def gradient(w1, w2, h=0.001):
            dw1 = (loss_function(w1 + h, w2) - loss_function(w1 - h, w2)) / (2 * h)
            dw2 = (loss_function(w1, w2 + h) - loss_function(w1, w2 - h)) / (2 * h)
            return dw1, dw2

        for i in range(num_steps):
            # Calculate gradient
            dw1, dw2 = gradient(initial_w1, initial_w2)

            # Update parameters
            initial_w1 -= learning_rate * dw1
            initial_w2 -= learning_rate * dw2

            # Update point
            new_point = surface.point_from_coordinates(initial_w1, initial_w2, loss_function(initial_w1, initial_w2))
            self.play(
                MoveToTarget(initial_point, new_point),
                Create(Arrow(new_point, new_point + DOWN * 0.2, buff=0, color=YELLOW, tip_length=0.1))
            )

            # Update loss history
            loss_value = loss_function(initial_w1, initial_w2)
            loss_history.append(loss_value)

            # Update loss curve
            if i > 0:
                new_loss_curve = Line(
                    *[surface.point_from_coordinates(initial_w1, initial_w2, loss_function(initial_w1, initial_w2)) for _ in range(i+1)],
                    color=GREEN
                )
                self.play(Transform(loss_curve, new_loss_curve))

            learning_rate *= 0.9  # Diminishing learning rate

        # Add axes labels
        w1_axis = Tex("w₁").next_to(surface, DOWN + LEFT, buff=0.5)
        w2_axis = Tex("w₂").next_to(surface, DOWN + RIGHT, buff=0.5)
        loss_axis = Tex("Loss").next_to(surface, UP, buff=0.5)

        self.play(Write(w1_axis), Write(w2_axis), Write(loss_axis))

        self.wait(2)
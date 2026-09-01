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
        initial_point = Dot(surface.point_from_parametric_point(initial_w1, initial_w2), color=RED)
        self.play(Create(initial_point))

        # Loss curve
        loss_curve = Line(start=np.array([0, 0, 0]), end=np.array([0, 0, 0]), color=GREEN)
        loss_values = []
        loss_graph = NumberPlane(x_range=[-10, 10], y_range=[0, 20], x_length=10, y_length=5)
        loss_graph.add_coordinate_labels()
        loss_graph.shift(DOWN * 2)
        self.play(Create(loss_graph))

        # Gradient descent parameters
        learning_rate = 0.2
        num_steps = 8

        # Gradient function
        def gradient(w1, w2):
            dw1 = 2 * w1 + 5 * np.cos(w1 * 5) * np.cos(w2 * 5)
            dw2 = 2 * w2 - 5 * np.sin(w1 * 5) * np.sin(w2 * 5)
            return np.array([dw1, dw2])

        current_w1 = initial_w1
        current_w2 = initial_w2

        for i in range(num_steps):
            # Compute gradient
            grad = gradient(current_w1, current_w2)

            # Update position
            current_w1 -= learning_rate * grad[0]
            current_w2 -= learning_rate * grad[1]

            # Move the dot
            new_point = surface.point_from_parametric_point(current_w1, current_w2)
            self.play(
                MoveToTarget(initial_point, new_point),
                Create(Arrow(initial_point.get_center(), initial_point.get_center() + 0.2 * grad, color=YELLOW))
            )

            # Update loss curve
            loss_value = loss_function(current_w1, current_w2)
            loss_values.append(loss_value)
            
            if i > 0:
                new_loss_curve = Line(
                    start=loss_graph.coords_to_point(i-1, loss_values[i-1]),
                    end=loss_graph.coords_to_point(i, loss_value),
                    color=GREEN
                )
                self.play(Transform(loss_curve, new_loss_curve))
            else:
                loss_curve = Line(
                    start=loss_graph.coords_to_point(0, loss_value),
                    end=loss_graph.coords_to_point(0, loss_value),
                    color=GREEN
                )
                self.play(Create(loss_curve))

            # Diminish learning rate
            learning_rate *= 0.95

        # Add labels
        w1_label = Tex("w₁").next_to(surface, DOWN + LEFT)
        w2_label = Tex("w₂").next_to(surface, DOWN + RIGHT)
        loss_label = Tex("Loss").next_to(surface, UP)

        self.play(Write(w1_label), Write(w2_label), Write(loss_label))
        self.wait(2)
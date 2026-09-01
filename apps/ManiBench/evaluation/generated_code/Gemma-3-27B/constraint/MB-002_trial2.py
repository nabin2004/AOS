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
        self.wait(1)

        # Loss curve
        loss_curve = Axes(
            x_range=[0, 10],
            y_range=[0, 20],
            x_length=5,
            y_length=3,
            axis_config={"include_numbers": False}
        )
        loss_curve.add_coordinate_labels(x_range=[0, 5, 10], y_range=[0, 10, 20])
        loss_curve_line = always_redraw(lambda: Line(loss_curve.c2p(0, 0), loss_curve.c2p(self.iteration, loss_function(initial_w1 - self.iteration * 0.2, initial_w2 - self.iteration * 0.2))))
        loss_curve.add(loss_curve_line)
        loss_curve.add(Tex("Loss").next_to(loss_curve, UP))
        loss_curve.add(Tex("Iteration").next_to(loss_curve, RIGHT))
        self.play(Create(loss_curve))

        self.iteration = 0
        # Gradient descent steps
        learning_rate = 0.2
        for i in range(5):
            # Calculate gradient
            dw1 = 2 * initial_w1 + 5 * np.cos(initial_w1 * 5) * np.sin(initial_w2 * 5)
            dw2 = 2 * initial_w2 - 5 * np.sin(initial_w1 * 5) * np.cos(initial_w2 * 5)

            # Gradient vector
            gradient = [-dw1 * learning_rate, -dw2 * learning_rate, 0]
            gradient_arrow = Arrow(dot.get_center(), dot.get_center() + gradient, color=RED)

            # Update point
            new_w1 = initial_w1 + gradient[0]
            new_w2 = initial_w2 + gradient[1]
            new_point = [new_w1, new_w2, loss_function(new_w1, new_w2)]

            # Animate
            self.play(
                Create(gradient_arrow),
                MoveToTarget(dot, new_point),
                Update(loss_curve_line)
            )
            self.iteration += 1
            self.wait(0.5)
            gradient_arrow.clear()

            initial_w1 = new_w1
            initial_w2 = new_w2
            dot.move_to(new_point)
            learning_rate *= 0.8  # Diminish learning rate

        # Display final result
        final_iteration_label = Tex(f"Iteration: {self.iteration}").to_edge(UP)
        self.play(Write(final_iteration_label))
        self.wait(2)
from manim import *

class GradientDescent2D(Scene):
    def construct(self):
        # Define the loss function
        def loss_function(w1, w2):
            return (w1**2 + w2**2) + np.sin(w1) * np.cos(w2)

        # Create axes
        axes = ThreeDAxes(x_range=[-3, 3], y_range=[-3, 3], z_range=[0, 10], axis_config={"include_numbers": True})
        axes.add_coordinate_labels(x_label="w₁", y_label="w₂", z_label="Loss")

        # Create the loss surface
        surface = Surface(
            lambda u, v: axes.coordinate_to_point(u, v, loss_function(u, v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            color=BLUE,
            fill_opacity=0.5
        )

        # Initial point
        w1_init = 2.0
        w2_init = 2.0
        dot = Dot(axes.coordinate_to_point(w1_init, w2_init, loss_function(w1_init, w2_init)), color=RED)

        # Loss curve
        loss_curve = Line(axes.c2p(0, 0, 0), axes.c2p(0, 0, 0), color=GREEN)
        loss_history = []

        # Gradient descent parameters
        learning_rate = 0.3
        num_steps = 7

        self.play(Create(axes), Create(surface))
        self.play(FadeIn(dot))
        self.wait(0.5)

        # Gradient descent loop
        w1 = w1_init
        w2 = w2_init
        for step in range(num_steps):
            # Calculate gradient (numerical approximation)
            delta = 0.001
            dw1 = (loss_function(w1 + delta, w2) - loss_function(w1 - delta, w2)) / (2 * delta)
            dw2 = (loss_function(w1, w2 + delta) - loss_function(w1, w2 - delta)) / (2 * delta)
            gradient = np.array([dw1, dw2, 0])

            # Update position
            w1_new = w1 - learning_rate * dw1
            w2_new = w2 - learning_rate * dw2
            new_pos = axes.coordinate_to_point(w1_new, w2_new, loss_function(w1_new, w2_new))

            # Create arrow
            arrow = Arrow(dot.get_center(), new_pos, buff=0.1, color=YELLOW)

            # Update loss curve
            loss_value = loss_function(w1, w2)
            loss_history.append(loss_value)
            loss_curve.become(Line(axes.c2p(0, 0, 0), axes.c2p(0, 0, loss_value), color=GREEN))

            # Animate
            self.play(Create(arrow), MoveToTarget(dot, new_pos), run_time=0.5)
            self.play(Transform(loss_curve, loss_curve), run_time=0.5)
            self.play(FadeOut(arrow), run_time=0.3)

            w1 = w1_new
            w2 = w2_new
            learning_rate *= 0.9

        final_text = Text("Converged!", font_size=28, color=GREEN).next_to(dot, UP)
        self.play(Write(final_text))
        self.wait(1)
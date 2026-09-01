from manim import *

class GradientDescent(Scene):
    def __init__(self):
        super().__init__()
        self.w1_start = 3
        self.w2_start = 3
        self.learning_rate = 0.5
        self.num_steps = 7
        self.loss_history = []

    def loss_function(self, w1, w2):
        return (w1 - 2)**2 + (w2 - 1)**2

    def gradient(self, w1, w2):
        dw1 = 2 * (w1 - 2)
        dw2 = 2 * (w2 - 1)
        return dw1, dw2

    def construct(self):
        axes = ThreeDAxes(
            x_range=[-1, 5],
            y_range=[-1, 5],
            z_range=[0, 10],
            x_length=6,
            y_length=6,
            z_length=5,
            axis_config={"include_numbers": True},
        )
        axes.add_coordinate_labels(x_label="w₁", y_label="w₂", z_label="Loss")
        self.play(Create(axes))

        surface = Surface(
            lambda w1, w2: self.loss_function(w1, w2),
            x_range=[-1, 5],
            y_range=[-1, 5],
            resolution=(50, 50),
            color=BLUE_E
        )
        self.play(Create(surface))

        dot = Dot3D(
            point=[self.w1_start, self.w2_start, self.loss_function(self.w1_start, self.w2_start)],
            color=RED
        )
        self.play(Create(dot))

        loss_curve = Line(start=ORIGIN, end=ORIGIN, color=GREEN)
        self.play(Create(loss_curve))

        w1 = self.w1_start
        w2 = self.w2_start
        for i in range(self.num_steps):
            dw1, dw2 = self.gradient(w1, w2)
            w1 -= self.learning_rate * dw1
            w2 -= self.learning_rate * dw2
            loss = self.loss_function(w1, w2)
            self.loss_history.append(loss)

            new_dot = Dot3D(
                point=[w1, w2, loss],
                color=RED
            )

            gradient_vector = Vector3D(
                start=[w1, w2, loss],
                end=[w1 - self.learning_rate * dw1, w2 - self.learning_rate * dw2, loss],
                color=YELLOW
            )

            self.play(
                Create(gradient_vector),
                Transform(dot, new_dot)
            )
            self.play(FadeOut(gradient_vector))

            loss_curve = Line(
                start=ORIGIN,
                end=[i, loss],
                color=GREEN
            )
            self.play(Transform(loss_curve, loss_curve))

            self.learning_rate *= 0.8

        self.wait(2)
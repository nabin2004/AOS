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
        return 2 * (w1 - 2), 2 * (w2 - 1)

    def construct(self):
        axes = ThreeDAxes(
            x_range=[-2, 6],
            y_range=[-1, 5],
            z_range=[0, 10],
            x_length=6,
            y_length=6,
            z_length=5,
            axis_config={"include_numbers": True},
        )
        axes.add_coordinate_labels(x_unit_size=1, y_unit_size=1, z_unit_size=1)
        axes.x_axis.label = Tex("w₁")
        axes.y_axis.label = Tex("w₂")
        axes.z_axis.label = Tex("Loss")

        surface = Surface(
            lambda w1, w2: self.loss_function(w1, w2),
            x_range=[-2, 6],
            y_range=[-1, 5],
            resolution=(50, 50),
            color=BLUE_E
        )

        dot = Dot3D(
            point=[self.w1_start, self.w2_start, self.loss_function(self.w1_start, self.w2_start)],
            color=RED
        )

        loss_curve = Line(start=ORIGIN, end=ORIGIN, color=GREEN)
        loss_text = Tex("Loss: ")
        loss_text.next_to(loss_curve, UP)

        self.play(Create(axes), Create(surface))
        self.play(Create(dot))

        w1 = self.w1_start
        w2 = self.w2_start

        for i in range(self.num_steps):
            grad_x, grad_y = self.gradient(w1, w2)
            step_size = self.learning_rate * (1 / (i + 1))
            w1 -= step_size * grad_x
            w2 -= step_size * grad_y

            new_z = self.loss_function(w1, w2)
            new_point = [w1, w2, new_z]

            arrow = Arrow3D(
                start=dot.get_center(),
                end=new_point,
                color=YELLOW,
                buff=0.1
            )

            self.play(
                Create(arrow),
                Transform(dot, Dot3D(point=new_point, color=RED)),
                Update(loss_curve, lambda m: m.become(Line(start=loss_curve.get_end(), end=new_point)))
            )
            self.loss_history.append(new_z)
            loss_text.become(Tex(f"Loss: {new_z:.2f}"))
            self.play(FadeOut(arrow))

        self.wait(2)
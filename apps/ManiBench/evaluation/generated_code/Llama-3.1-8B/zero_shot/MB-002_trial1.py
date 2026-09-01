from manim import *

class GradientDescent(Scene):
    def construct(self):
        # Define the loss function
        def loss(w1, w2):
            return (w1 - 2)**2 + (w2 - 3)**2

        # Create a 3D axes
        axes = ThreeDAxes(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            z_range=[0, 10, 1],
            axis_config={"include_tip": False},
        )

        # Create a surface representing the loss function
        surface = ParametricSurface(
            lambda u, v: [u, v, loss(u, v)],
            t_range=[-5, 5, 100],
            v_range=[-5, 5, 100],
            resolution=(50, 50),
        )

        # Create a dot at a high-loss location
        dot = Dot3D(
            point=[2, 3, loss(2, 3)],
            radius=0.1,
            color=RED,
        )

        # Create a loss curve
        loss_curve = always_redraw(
            lambda: Line(
                [axes.c2p(0, 0, 0), axes.c2p(0, 0, loss(0, 0))],
                color=RED,
            )
        )

        # Create arrows indicating gradient direction
        arrows = []

        # Animate the gradient descent
        for i in range(10):
            # Compute the gradient at the dot's position
            gradient = [-2 * (dot.get_point()[0] - 2), -2 * (dot.get_point()[1] - 3)]

            # Move the dot in the direction of the negative gradient
            dot.move_to(dot.get_point() + gradient * 0.1)

            # Update the loss curve
            loss_curve.become(
                Line(
                    [axes.c2p(0, 0, 0), axes.c2p(0, 0, loss(dot.get_point()[0], dot.get_point()[1])],
                    color=RED,
                )
            )

            # Add an arrow indicating the gradient direction
            arrow = Arrow(
                start=dot.get_point(),
                end=dot.get_point() + gradient * 0.1,
                color=YELLOW,
            )
            arrows.append(arrow)

            # Add the dot and arrow to the scene
            self.play(
                MoveAlongPath(dot, axes.c2p(dot.get_point()[0], dot.get_point()[1], loss(dot.get_point()[0], dot.get_point()[1])), run_time=0.5),
                run_time=0.5,
            )
            self.play(FadeIn(arrow), run_time=0.5)
            self.wait(0.5)

        # Add the axes and surface to the scene
        self.add(axes, surface, dot, loss_curve)
        self.play(FadeIn(arrows[0]), run_time=0.5)
        for i in range(1, len(arrows)):
            self.play(FadeIn(arrows[i]), run_time=0.5)
            self.wait(0.5)

        # Label the axes
        self.add(
            Text("w₁", font_size=24, color=WHITE).to_edge(LEFT, buff=0.1),
            Text("w₂", font_size=24, color=WHITE).to_edge(RIGHT, buff=0.1),
            Text("Loss", font_size=24, color=WHITE).to_edge(DOWN, buff=0.1),
        )
from manim import *
import numpy as np


class Greatest(ThreeDScene):
    def construct(self):
        # ----------------------------------------------------
        # 1. 2D Number Plane
        # ----------------------------------------------------
        plane = NumberPlane(
            background_line_style={
                "stroke_opacity": 0.45,
                "stroke_width": 1,
            }
        )

        self.play(Create(plane), run_time=3)

        # ----------------------------------------------------
        # 2. Show 3D Axes
        # ----------------------------------------------------
        axes3d = ThreeDAxes()

        self.play(Create(axes3d), run_time=2)

        # ----------------------------------------------------
        # 3. Smooth Camera Rotation
        # ----------------------------------------------------
        self.move_camera(
            phi=75 * DEGREES,
            theta=30 * DEGREES,
            run_time=3,
            rate_func=smooth,
        )

        self.wait(1)

        # ----------------------------------------------------
        # 4. Return Back to Front View
        # ----------------------------------------------------
        self.move_camera(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            run_time=2,
            rate_func=smooth,
        )

        self.wait(0.5)

        # Remove 3D axes
        self.play(FadeOut(axes3d))

        # ----------------------------------------------------
        # 5. Euler Circle
        # ----------------------------------------------------
        # Euler Circle
        circle = Circle(radius=2, color=BLUE)

        tracker = ValueTracker(0)   # <-- FIRST

        radius = always_redraw(
            lambda: Line(
                circle.get_center(),
                circle.point_at_angle(tracker.get_value()),
                color=YELLOW,
            )
        )

        moving_dot = always_redraw(
            lambda: Dot(
                circle.point_at_angle(tracker.get_value()),
                color=RED,
            )
        )

        angle_arc = always_redraw(
            lambda: Arc(
                radius=0.5,
                start_angle=0,
                angle=tracker.get_value(),
                color=GREEN,
            )
        )
        moving_dot = always_redraw(
            lambda: Dot(
                circle.point_at_angle(tracker.get_value()),
                color=RED,
                radius=0.08,
            )
        )

        angle_arc = always_redraw(
            lambda: Arc(
                radius=0.5,
                start_angle=0,
                angle=tracker.get_value(),
                color=GREEN,
            )
        )

        label = MathTex(r"e^{i\theta}")
        label.to_corner(UL)

        self.play(Create(circle))
        self.play(
            FadeIn(moving_dot),
            Create(radius),
            Create(angle_arc),
            Write(label),
        )

        # ----------------------------------------------------
        # 6. Sine Graph Axes
        # ----------------------------------------------------
        graph_axes = Axes(
            x_range=[0, TAU + 0.5],
            y_range=[-1.5, 1.5],
            x_length=5,
            y_length=3,
            tips=False,
        )

        graph_axes.shift(RIGHT * 4)

        self.play(Create(graph_axes))

        # ----------------------------------------------------
        # Horizontal Projection Line
        # ----------------------------------------------------
        projection = always_redraw(
            lambda: DashedLine(
                moving_dot.get_center(),
                graph_axes.c2p(0, np.sin(tracker.get_value())),
                color=GRAY,
            )
        )

        self.add(projection)

        # ----------------------------------------------------
        # Moving Point on Graph
        # ----------------------------------------------------
        graph_dot = always_redraw(
            lambda: Dot(
                graph_axes.c2p(
                    tracker.get_value(),
                    np.sin(tracker.get_value()),
                ),
                color=YELLOW,
            )
        )

        self.add(graph_dot)

        # ----------------------------------------------------
        # Trace the Sine Wave
        # ----------------------------------------------------
        sine_curve = always_redraw(
            lambda: graph_axes.plot(
                lambda x: np.sin(x),
                x_range=[0, tracker.get_value()],
                color=BLUE,
            )
        )

        self.add(sine_curve)

        # ----------------------------------------------------
        # Rotate Around Circle
        # ----------------------------------------------------
        self.play(
            tracker.animate.set_value(TAU),
            run_time=6,
            rate_func=linear,
        )

        self.play(
            tracker.animate.set_value(2 * TAU),
            run_time=6,
            rate_func=linear,
        )

        self.wait()

        # ----------------------------------------------------
        # 7. Fade Everything Except Sine Wave
        # ----------------------------------------------------
        self.play(
            FadeOut(circle),
            FadeOut(radius),
            FadeOut(moving_dot),
            FadeOut(angle_arc),
            FadeOut(label),
            FadeOut(projection),
            FadeOut(graph_dot),
            FadeOut(graph_axes),
            FadeOut(plane),
        )

        self.wait(0.5)

        # ----------------------------------------------------
        # 8. Brand Reveal
        # ----------------------------------------------------
        brand = Text(
            "RukMini",
            font_size=80,
            weight=BOLD,
            color=WHITE,
        )

        self.play(
            Write(brand),
            run_time=2,
        )

        self.play(
            brand.animate.scale(1.08),
            run_time=0.8,
            rate_func=there_and_back,
        )

        self.wait(2)
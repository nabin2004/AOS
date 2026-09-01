from manim import *
import numpy as np


class DeterminantGeometric(Scene):
    def construct(self):
        # Define the transformation matrix
        a, b, c, d = 2, 1, 0.5, 1.5
        matrix = np.array([[a, b], [c, d]])
        det_val = np.linalg.det(matrix)

        # Title
        title = Text("Geometric Interpretation of the Determinant", font_size=36)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(0.5)

        # Create coordinate axes
        axes = Axes(
            x_range=[-1, 5, 1],
            y_range=[-1, 4, 1],
            x_length=7,
            y_length=5,
            axis_config={"include_numbers": True, "font_size": 20},
            tips=True,
        ).shift(DOWN * 0.3 + LEFT * 1)

        self.play(Create(axes), run_time=1)

        # Unit basis vectors
        origin = axes.c2p(0, 0)
        u_end = axes.c2p(1, 0)
        v_end = axes.c2p(0, 1)

        # Draw unit vectors
        vec_u = Arrow(origin, u_end, buff=0, color=BLUE, stroke_width=4)
        vec_v = Arrow(origin, v_end, buff=0, color=GREEN, stroke_width=4)

        u_label = MathTex(r"\vec{u}", color=BLUE, font_size=30).next_to(vec_u, DOWN, buff=0.15)
        v_label = MathTex(r"\vec{v}", color=GREEN, font_size=30).next_to(vec_v, LEFT, buff=0.15)

        self.play(GrowArrow(vec_u), Write(u_label))
        self.play(GrowArrow(vec_v), Write(v_label))

        # Unit parallelogram
        unit_parallelogram = Polygon(
            axes.c2p(0, 0),
            axes.c2p(1, 0),
            axes.c2p(1, 1),
            axes.c2p(0, 1),
            color=YELLOW,
            fill_color=YELLOW,
            fill_opacity=0.3,
            stroke_width=2,
        )

        self.play(Create(unit_parallelogram))

        # Original area label
        area_label = MathTex(r"\text{Original Area} = 1", font_size=30, color=YELLOW)
        area_label.to_edge(RIGHT, buff=0.5).shift(UP * 1.5)
        self.play(Write(area_label))

        # Display the 2x2 matrix
        matrix_tex = MathTex(
            r"A = \begin{bmatrix} "
            + f"{a} & {b}"
            + r" \\ "
            + f"{c} & {d}"
            + r" \end{bmatrix}",
            font_size=30,
            color=WHITE,
        )
        matrix_tex.to_edge(RIGHT, buff=0.5).shift(UP * 0.5)
        self.play(Write(matrix_tex))
        self.wait(0.5)

        # Determinant value tracker
        t_tracker = ValueTracker(0)

        # Dynamic determinant label
        det_label = always_redraw(
            lambda: MathTex(
                r"\det(A) = "
                + f"{1.0 * (1 - t_tracker.get_value()) + det_val * t_tracker.get_value():.2f}",
                font_size=30,
                color=RED,
            ).to_edge(RIGHT, buff=0.5).shift(DOWN * 0.3)
        )

        new_area_label = always_redraw(
            lambda: MathTex(
                r"\text{Area} = |{\det(A)}| = "
                + f"{abs(1.0 * (1 - t_tracker.get_value()) + det_val * t_tracker.get_value()):.2f}",
                font_size=30,
                color=ORANGE,
            ).to_edge(RIGHT, buff=0.5).shift(DOWN * 1.1)
        )

        self.play(Write(det_label), Write(new_area_label))

        # Transformed endpoints as functions of t
        def get_transformed_parallelogram():
            t = t_tracker.get_value()
            # Interpolate: (1-t)*I + t*A
            M = (1 - t) * np.eye(2) + t * matrix

            p0 = axes.c2p(0, 0)
            corners_orig = np.array([[1, 0], [1, 1], [0, 1]])
            transformed = [M @ corner for corner in corners_orig]
            p1 = axes.c2p(transformed[0][0], transformed[0][1])
            p2 = axes.c2p(transformed[1][0], transformed[1][1])
            p3 = axes.c2p(transformed[2][0], transformed[2][1])

            return Polygon(
                p0, p1, p2, p3,
                color=YELLOW,
                fill_color=ORANGE,
                fill_opacity=0.3,
                stroke_width=2,
            )

        # Replace static parallelogram with dynamic one
        dynamic_parallelogram = always_redraw(get_transformed_parallelogram)

        # Transformed vectors
        def get_transformed_u():
            t = t_tracker.get_value()
            M = (1 - t) * np.eye(2) + t * matrix
            new_u = M @ np.array([1, 0])
            return Arrow(
                axes.c2p(0, 0),
                axes.c2p(new_u[0], new_u[1]),
                buff=0,
                color=BLUE,
                stroke_width=4,
            )

        def get_transformed_v():
            t = t_tracker.get_value()
            M = (1 - t) * np.eye(2) + t * matrix
            new_v = M @ np.array([0, 1])
            return Arrow(
                axes.c2p(0, 0),
                axes.c2p(new_v[0], new_v[1]),
                buff=0,
                color=GREEN,
                stroke_width=4,
            )

        dynamic_u = always_redraw(get_transformed_u)
        dynamic_v = always_redraw(get_transformed_v)

        # Dynamic labels for vectors
        dynamic_u_label = always_redraw(
            lambda: MathTex(r"A\vec{u}", color=BLUE, font_size=28).next_to(
                get_transformed_u().get_end(), DOWN, buff=0.15
            )
        )
        dynamic_v_label = always_redraw(
            lambda: MathTex(r"A\vec{v}", color=GREEN, font_size=28).next_to(
                get_transformed_v().get_end(), LEFT, buff=0.15
            )
        )

        # Remove static elements and add dynamic ones
        self.play(
            FadeOut(unit_parallelogram),
            FadeOut(vec_u),
            FadeOut(vec_v),
            FadeOut(u_label),
            FadeOut(v_label),
            FadeOut(area_label),
        )

        self.add(dynamic_parallelogram, dynamic_u, dynamic_v, dynamic_u_label, dynamic_v_label)
        self.wait(0.3)

        # Animate the transformation
        self.play(
            t_tracker.animate.set_value(1),
            run_time=4,
            rate_func=smooth,
        )

        self.wait(0.5)

        # Final highlight
        final_box = SurroundingRectangle(new_area_label, color=ORANGE, buff=0.15)
        self.play(Create(final_box))

        # Final summary
        final_text = MathTex(
            r"\text{New Area} = |\det(A)| = " + f"{abs(det_val):.2f}",
            font_size=34,
            color=ORANGE,
        ).to_edge(DOWN, buff=0.4)
        self.play(Write(final_text))

        self.wait(2)
from manim import *


class EigenvectorScene(Scene):
    def construct(self):
        title = Text("Eigenvectors in 2D", font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # --- Setup: Define a 2D space and a transformation matrix ---
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=7,
            y_length=7,
            axis_config={"include_numbers": True},
            tips=False,
        ).to_edge(DOWN, buff=0.5)

        axes.set_title(Tex("x", font_size=24).to_edge(RIGHT))
        axes.set_x_label("x")  # FIXED: removed direction=RIGHT
        axes.set_y_label("y")  # FIXED: removed direction=UP

        axes_x = axes.get_x_axis()
        axes_y = axes.get_y_axis()

        # Draw axes
        line_x = axes.get_x_axis().get_line()
        line_y = axes.get_y_axis().get_line()

        # Add a vector for demonstration
        arrow = Arrow(axes.c2p(1.5, 1.5), axes.c2p(1.5, 2.5), buff=0)
        arrow.set_color(BLUE)

        # Define the transformation matrix (for a simple rotation)
        # Rotation by 90 degrees: [[0, -1], [1, 0]]
        # Eigenvectors for rotation are [1, 1] and [-1, 1] for 45/135 degree rotations.

        # We will use a simple diagonal matrix for simplicity, e.g., [[2, 0], [0, 1]]
        # Eigenvectors for [[2, 0], [0, 1]] are [1, 0] and [0, 1]

        # Define the transformation matrix M
        M = Matrix([[2, 0], [0, 1]], color=YELLOW).scale(0.7).shift(DOWN * 0.5)

        # Draw the transformation matrix
        M_display = M.to_matrix(scale=0.7).shift(DOWN * 0.5)
        M_display.scale(0.7).set_color(YELLOW)

        # Draw the transformation
        transform_arrow = Arrow(axes.c2p(0, 0), axes.c2p(2, 1), buff=0)
        transform_arrow.set_color(YELLOW)

        # Add text explaining the concept

        # 1. Concept Introduction
        concept_text = (
            Text("Eigenvectors", font_size=28)
            .next_to(title, DOWN, buff=0.5)
            .to_edge(LEFT)
            .set_color(GREEN)
        )
        concept_text_2 = (
            Text("Eigenvectors", font_size=28)
            .next_to(concept_text, DOWN, buff=0.3)
            .set_color(GREEN)
        )

        # 2. Explanation of Eigenvectors

        # Vector 1: [1, 0] (x-axis)
        vec1_start = axes.c2p(0, 0)
        vec1_end = axes.c2p(1, 0)
        vec1 = Line(vec1_start, vec1_end, color=RED, stroke_width=5)
        vec1_label = (
            MathTex("v_1 = [1, 0]", color=RED)
            .next_to(vec1, DOWN, buff=0.2)
            .shift(RIGHT)
        )

        # Vector 2: [0, 1] (y-axis)
        vec2_start = axes.c2p(0, 0)
        vec2_end = axes.c2p(0, 1)
        vec2 = Line(vec2_start, vec2_end, color=GREEN, stroke_width=5)
        vec2_label = (
            MathTex("v_2 = [0, 1]", color=GREEN)
            .next_to(vec2, DOWN, buff=0.2)
            .shift(RIGHT)
        )

        # 3. Transformation

        # Transform the basis vectors
        transform_vec1 = vec1.copy().shift(RIGHT * 1.5)
        transform_vec2 = vec2.copy().shift(UP * 1.5)

        transform_vec1.set_color(RED)
        transform_vec2.set_color(GREEN)

        # Draw the transformed vectors
        transform_arrow_1 = Arrow(vec1.get_end(), transform_vec1.get_end(), buff=0.2)
        transform_arrow_1.set_color(RED)

        transform_arrow_2 = Arrow(vec2.get_end(), transform_vec2.get_end(), buff=0.2)
        transform_arrow_2.set_color(GREEN)

        # 4. Conclusion
        conclusion_text = Text(
            "They are only scaled, not rotated.", font_size=24
        ).to_edge(DOWN)
        conclusion_text.next_to(concept_text_2, DOWN, buff=0.5).set_color(BLUE)

        self.play(Write(concept_text), run_time=1.5)
        self.play(FadeIn(concept_text_2), run_time=1)
        self.play(
            FadeIn(vec1_label),
            FadeIn(vec1),
            FadeIn(vec2_label),
            FadeIn(vec2),
            transform_arrow_1,
            transform_arrow_2,
            run_time=2,
        )
        self.play(
            Transform(transform_vec1, transform_vec1.copy().shift(RIGHT * 1.5)),
            Transform(transform_vec2, transform_vec2.copy().shift(UP * 1.5)),
            run_time=2,
        )

        self.play(
            FadeOut(vec1_label),
            FadeOut(vec2_label),
            FadeOut(vec1),
            FadeOut(vec2),
            FadeOut(transform_arrow_1),
            FadeOut(transform_arrow_2),
            run_time=1.5,
        )

        self.play(FadeIn(conclusion_text), run_time=1)

        self.wait(2)

        self.play(FadeOut(title))
        self.wait(1)

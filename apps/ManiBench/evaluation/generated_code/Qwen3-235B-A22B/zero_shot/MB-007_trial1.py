from manim import *

class BayesBox(Scene):
    def construct(self):
        # Hypothetical values
        total_population = 1000
        sick_count = 1
        not_sick_count = total_population - sick_count

        # Test accuracy: 95% true positive, 95% true negative
        true_positive_rate = 0.95
        false_positive_rate = 0.05

        sick_and_positive = round(sick_count * true_positive_rate)  # P(sick ∩ +)
        sick_and_negative = sick_count - sick_and_positive          # P(sick ∩ −)
        not_sick_and_positive = round(not_sick_count * false_positive_rate)  # P(not-sick ∩ +)
        not_sick_and_negative = not_sick_count - not_sick_and_positive       # P(not-sick ∩ −)

        # Define rectangle dimensions
        width = 8
        height = 6
        rect = Rectangle(width=width, height=height, color=WHITE)
        rect.move_to(ORIGIN)

        # Divide into 4 quadrants
        # Vertical split: sick vs not-sick (1/1000 vs 999/1000)
        sick_width = width * (sick_count / total_population)
        not_sick_width = width - sick_width

        # Horizontal split: positive vs negative (based on test accuracy)
        positive_height = height * ((sick_and_positive + not_sick_and_positive) / total_population)
        negative_height = height - positive_height

        # Draw vertical and horizontal dividers
        vertical_line = Line(
            start=UP * (height / 2) + RIGHT * (sick_width - width / 2),
            end=DOWN * (height / 2) + RIGHT * (sick_width - width / 2),
            color=WHITE
        )
        horizontal_line = Line(
            start=LEFT * (width / 2) + UP * (positive_height - height / 2),
            end=RIGHT * (width / 2) + UP * (positive_height - height / 2),
            color=WHITE
        )

        # Labels for axes
        sick_label = Text("Sick", font_size=24).next_to(vertical_line, UP, buff=0.5).shift(LEFT * (width / 2 - sick_width / 2))
        not_sick_label = Text("Not Sick", font_size=24).next_to(vertical_line, UP, buff=0.5).shift(RIGHT * (width / 2 - not_sick_width / 2))
        pos_label = Text("Test +", font_size=24).rotate(90 * DEGREES).next_to(horizontal_line, LEFT, buff=0.5).shift(UP * (height / 2 - positive_height / 2))
        neg_label = Text("Test −", font_size=24).rotate(90 * DEGREES).next_to(horizontal_line, LEFT, buff=0.5).shift(DOWN * (height / 2 - negative_height / 2))

        # Quadrant labels
        tl_text = Text(f"{sick_and_positive}\nP(sick ∩ +)", font_size=18, alignment="center")
        tr_text = Text(f"{not_sick_and_positive}\nP(not-sick ∩ +)", font_size=18, alignment="center")
        bl_text = Text(f"{sick_and_negative}\nP(sick ∩ −)", font_size=18, alignment="center")
        br_text = Text(f"{not_sick_and_negative}\nP(not-sick ∩ −)", font_size=18, alignment="center")

        # Position texts in quadrants
        tl_text.move_to(LEFT * (width / 2 - sick_width / 2) + UP * (height / 2 - positive_height / 2))
        tr_text.move_to(RIGHT * (width / 2 - not_sick_width / 2) + UP * (height / 2 - positive_height / 2))
        bl_text.move_to(LEFT * (width / 2 - sick_width / 2) + DOWN * (height / 2 - negative_height / 2))
        br_text.move_to(RIGHT * (width / 2 - not_sick_width / 2) + DOWN * (height / 2 - negative_height / 2))

        # Animate: Draw rectangle
        self.play(Create(rect))
        self.wait(0.5)

        # Add axis labels
        self.play(
            Write(sick_label),
            Write(not_sick_label),
            Write(pos_label),
            Write(neg_label)
        )
        self.wait(0.5)

        # Animate vertical and horizontal lines
        self.play(Create(vertical_line), Create(horizontal_line))
        self.wait(0.5)

        # Show counts in each quadrant
        self.play(
            Write(tl_text),
            Write(tr_text),
            Write(bl_text),
            Write(br_text)
        )
        self.wait(1)

        # Highlight top row (all who tested positive)
        top_row = Rectangle(
            width=width,
            height=positive_height,
            fill_color=YELLOW,
            fill_opacity=0.3,
            stroke_width=0
        ).align_to(rect, UP).align_to(rect, LEFT)
        self.play(FadeIn(top_row))
        self.wait(0.5)

        # Highlight top-left (sick and positive)
        tl_highlight = Rectangle(
            width=sick_width,
            height=positive_height,
            fill_color=RED,
            fill_opacity=0.4,
            stroke_width=4,
            color=RED
        ).align_to(rect, UP).align_to(rect, LEFT)
        self.play(Create(tl_highlight))
        self.wait(1)

        # Show Bayes' theorem formula
        formula = MathTex(
            "P(", "\\text{sick}", " | ", "+", ") = \\frac{P(+ | \\text{sick}) \\cdot P(\\text{sick})}{P(+)}",
            font_size=48
        ).to_edge(UP * 3)
        self.play(Write(formula))
        self.wait(1)

        # Substitute with counts
        posterior = MathTex(
            "P(", "\\text{sick}", " | ", "+", ") = \\frac{", str(sick_and_positive), "}{", str(sick_and_positive), " + ", str(not_sick_and_positive), "}",
            font_size=48
        ).next_to(formula, DOWN)
        self.play(Write(posterior))
        self.wait(1)

        # Calculate final probability
        prob = sick_and_positive / (sick_and_positive + not_sick_and_positive) if (sick_and_positive + not_sick_and_positive) > 0 else 0
        result = MathTex(
            f"= {prob:.3f}", " \\approx ", f"{prob*100:.1f}\\%", font_size=48
        ).next_to(posterior, DOWN)
        self.play(Write(result))
        self.wait(2)

        # Explain the paradox
        explanation = Paragraph(
            "Even with a 95% accurate test,\n",
            "the low disease prevalence leads to\n",
            "many more false positives than true positives.",
            font_size=24,
            alignment="center"
        ).to_edge(DOWN)
        self.play(Write(explanation))
        self.wait(3)

        # Fade out everything
        self.play(
            *[FadeOut(mob) for mob in self.mobjects]
        )
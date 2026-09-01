from manim import *

class BayesTheorem(Scene):
    def construct(self):
        # Define colors
        sick_color = YELLOW
        not_sick_color = GREEN
        positive_color = RED
        negative_color = BLUE

        # Create the Bayes box
        rect = Rectangle(width=4, height=3, color=WHITE, stroke_width=2)
        self.play(Create(rect))

        # Divide into quadrants
        quadrant_width = rect.width / 2
        quadrant_height = rect.height / 2
        vertical_line = Line(rect.get_bottom_left() + UP * rect.height, rect.get_bottom_right() + UP * rect.height, color=GRAY)
        horizontal_line = Line(rect.get_bottom_left() + RIGHT * rect.width, rect.get_top_left() + RIGHT * rect.width, color=GRAY)
        self.play(Create(vertical_line), Create(horizontal_line))

        # Initial counts (hypothetical)
        sick_total = 10
        not_sick_total = 990
        total = sick_total + not_sick_total

        # Assume test accuracy: 95%
        accuracy = 0.95
        false_positive_rate = 1 - accuracy
        false_negative_rate = 1 - accuracy

        # Calculate counts for each quadrant
        sick_positive = int(sick_total * accuracy)
        sick_negative = sick_total - sick_positive
        not_sick_positive = int(not_sick_total * false_positive_rate)
        not_sick_negative = not_sick_total - not_sick_positive

        # Display counts in each quadrant
        tl_text = Tex(f"P(Sick ∩ +) = {sick_positive}", color=sick_color)
        tr_text = Tex(f"P(¬Sick ∩ +) = {not_sick_positive}", color=not_sick_color)
        bl_text = Tex(f"P(Sick ∩ −) = {sick_negative}", color=sick_color)
        br_text = Tex(f"P(¬Sick ∩ −) = {not_sick_negative}", color=not_sick_color)

        tl_text.move_to(rect.get_top_left() + DOWN * 0.5 + RIGHT * 0.5)
        tr_text.move_to(rect.get_top_right() + DOWN * 0.5 - RIGHT * 0.5)
        bl_text.move_to(rect.get_bottom_left() + UP * 0.5 + RIGHT * 0.5)
        br_text.move_to(rect.get_bottom_right() + UP * 0.5 - RIGHT * 0.5)

        self.play(Write(tl_text), Write(tr_text), Write(bl_text), Write(br_text))

        # Highlight sick population who tested positive
        self.play(Indicate(tl_text, color=sick_color))

        # Calculate P(Sick | +)
        total_positive = sick_positive + not_sick_positive
        if total_positive == 0:
            prob_sick_given_positive = 0
        else:
            prob_sick_given_positive = sick_positive / total_positive

        # Display final calculation
        calculation_text = MathTex(
            "P(Sick | +) = \\frac{P(Sick \\cap +)}{P(Sick \\cap +) + P(¬Sick \\cap +)}",
            "=",
            f"{sick_positive} / ({sick_positive} + {not_sick_positive})",
            "=",
            f"{prob_sick_given_positive:.2f}"
        )
        calculation_text.scale(0.7)
        calculation_text.move_to(rect.get_center() + DOWN * 2)

        self.play(Write(calculation_text))

        # Explain the paradox
        paradox_text = Text("Even with a 95% accurate test, the probability of being sick given a positive result is low due to the low prevalence of the disease.", font_size=24)
        paradox_text.move_to(rect.get_center() + DOWN * 3.5)
        self.play(Write(paradox_text))

        self.wait(5)
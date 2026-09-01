from manim import *

class BayesTheoremAnimation(Scene):
    def construct(self):
        # Parameters
        total_population = 1000
        sick_population = 1
        test_sensitivity = 0.95  # True positive rate
        test_specificity = 0.95  # True negative rate

        # Calculate values
        true_positives = sick_population * test_sensitivity
        false_negatives = sick_population * (1 - test_sensitivity)
        false_positives = (total_population - sick_population) * (1 - test_specificity)
        true_negatives = (total_population - sick_population) * test_specificity

        # Create Bayes box
        rect = Rectangle(width=4, height=3, color=WHITE)
        rect.set_fill(GREY_A, opacity=0.5)
        self.play(Create(rect))

        # Divide into quadrants
        line_v = Line(rect.get_bottom_left() + UP * 3, rect.get_bottom_right() + UP * 3, color=WHITE)
        line_h = Line(rect.get_bottom_left() + RIGHT * 4, rect.get_top_left() + RIGHT * 4, color=WHITE)
        self.play(Create(line_v), Create(line_h))

        # Labels
        sick_plus_label = Tex("P(Sick $\\cap$ +)", color=WHITE).move_to(rect.get_top_left() + DOWN * 0.5 + LEFT * 0.5)
        not_sick_plus_label = Tex("P(Not Sick $\\cap$ +)", color=WHITE).move_to(rect.get_top_right() + DOWN * 0.5 + RIGHT * 0.5)
        sick_minus_label = Tex("P(Sick $\\cap$ -)", color=WHITE).move_to(rect.get_bottom_left() + UP * 0.5 + LEFT * 0.5)
        not_sick_minus_label = Tex("P(Not Sick $\\cap$ -)", color=WHITE).move_to(rect.get_bottom_right() + UP * 0.5 + RIGHT * 0.5)

        self.play(Write(sick_plus_label), Write(not_sick_plus_label), Write(sick_minus_label), Write(not_sick_minus_label))

        # Initial counts
        sick_plus_text = Tex(f"{true_positives:.0f}", color=GREEN).move_to(rect.get_top_left() + DOWN * 0.5 + LEFT * 0.5 + DOWN * 0.7)
        not_sick_plus_text = Tex(f"{false_positives:.0f}", color=RED).move_to(rect.get_top_right() + DOWN * 0.5 + RIGHT * 0.5 + DOWN * 0.7)
        sick_minus_text = Tex(f"{false_negatives:.0f}", color=RED).move_to(rect.get_bottom_left() + UP * 0.5 + LEFT * 0.5 + UP * 0.7)
        not_sick_minus_text = Tex(f"{true_negatives:.0f}", color=GREEN).move_to(rect.get_bottom_right() + UP * 0.5 + RIGHT * 0.5 + UP * 0.7)

        self.play(Write(sick_plus_text), Write(not_sick_plus_text), Write(sick_minus_text), Write(not_sick_minus_text))

        # Highlight sick population who tested +
        highlight_rect = SurroundingRectangle(sick_plus_text, color=YELLOW, buff=0.2)
        self.play(Create(highlight_rect))
        self.wait(1)
        self.play(Uncreate(highlight_rect))

        # Bayes' theorem calculation
        bayes_theorem_text = Tex("P(Sick | +) = P(Sick $\\cap$ +) / (P(Sick $\\cap$ +) + P(Not Sick $\\cap$ +))", color=WHITE)
        bayes_theorem_text.move_to(rect.get_bottom() + UP * 1.5)
        self.play(Write(bayes_theorem_text))

        # Calculate and display final probability
        denominator = true_positives + false_positives
        if denominator == 0:
            probability = 0
        else:
            probability = true_positives / denominator

        probability_text = Tex(f"P(Sick | +) = {probability:.2f}", color=GREEN).next_to(bayes_theorem_text, DOWN)
        self.play(Write(probability_text))

        # Explanation
        paradox_text = Tex("Even with a 95% accurate test, the probability of being sick given a positive result is low due to the low disease prevalence.", color=YELLOW)
        paradox_text.move_to(rect.get_bottom() + UP * -1.5)
        self.play(Write(paradox_text))

        self.wait(3)
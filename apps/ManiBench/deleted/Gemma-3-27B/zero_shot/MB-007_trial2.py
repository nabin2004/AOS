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
        sick_plus_label = Tex("P(Sick $\\cap$ +)", color=WHITE).next_to(line_v, UP + LEFT)
        not_sick_plus_label = Tex("P(Not Sick $\\cap$ +)", color=WHITE).next_to(line_v, UP + RIGHT)
        sick_minus_label = Tex("P(Sick $\\cap$ -)", color=WHITE).next_to(line_v, DOWN + LEFT)
        not_sick_minus_label = Tex("P(Not Sick $\\cap$ -)", color=WHITE).next_to(line_v, DOWN + RIGHT)

        self.play(Write(sick_plus_label), Write(not_sick_plus_label), Write(sick_minus_label), Write(not_sick_minus_label))

        # Initial counts
        sick_plus_text = Tex(f"{true_positives:.0f}", color=GREEN).next_to(sick_plus_label, DOWN)
        not_sick_plus_text = Tex(f"{false_positives:.0f}", color=RED).next_to(not_sick_plus_label, DOWN)
        sick_minus_text = Tex(f"{false_negatives:.0f}", color=RED).next_to(sick_minus_label, DOWN)
        not_sick_minus_text = Tex(f"{true_negatives:.0f}", color=GREEN).next_to(not_sick_minus_label, DOWN)

        self.play(Write(sick_plus_text), Write(not_sick_plus_text), Write(sick_minus_text), Write(not_sick_minus_text))

        # Highlight sick population who tested positive
        highlight_rect = SurroundingRectangle(sick_plus_text, color=YELLOW, buff=0.2)
        self.play(Create(highlight_rect))

        # Bayes' theorem calculation
        bayes_theorem_text = Tex("P(Sick | +) = P(Sick $\\cap$ +) / (P(Sick $\\cap$ +) + P(Not Sick $\\cap$ +))", color=WHITE)
        bayes_theorem_text.to_edge(UP)
        self.play(Write(bayes_theorem_text))

        # Substitute values
        substituted_text = Tex(f"P(Sick | +) = {true_positives:.0f} / ({true_positives:.0f} + {false_positives:.0f})", color=WHITE)
        substituted_text.next_to(bayes_theorem_text, DOWN)
        self.play(Write(substituted_text))

        # Calculate and display final probability
        final_probability = true_positives / (true_positives + false_positives)
        final_probability_text = Tex(f"P(Sick | +) ≈ {final_probability:.2f}", color=WHITE)
        final_probability_text.next_to(substituted_text, DOWN)
        self.play(Write(final_probability_text))

        # Paradox explanation
        paradox_text = Tex("Despite 95% test accuracy, low prevalence leads to a high false positive rate.", color=YELLOW)
        paradox_text.next_to(final_probability_text, DOWN)
        self.play(Write(paradox_text))

        self.wait(5)
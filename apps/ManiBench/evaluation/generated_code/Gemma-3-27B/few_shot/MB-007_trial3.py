from manim import *

class BayesTheorem(Scene):
    def construct(self):
        # Parameters
        total_population = 1000
        sick_population = 1
        test_sensitivity = 0.95  # True positive rate
        test_specificity = 0.95  # True negative rate

        # Calculate values
        sick_and_positive = sick_population * test_sensitivity
        not_sick_and_positive = (total_population - sick_population) * (1 - test_specificity)
        sick_and_negative = sick_population * (1 - test_sensitivity)
        not_sick_and_negative = (total_population - sick_population) * test_specificity

        # Create Bayes box
        box = Rectangle(width=4, height=3, color=WHITE)
        box.set_fill(opacity=0.1)

        # Quadrant labels
        tl_label = MathTex("P(\\text{Sick} \\cap +)").to_edge(TL)
        tr_label = MathTex("P(\\text{Not Sick} \\cap +)").to_edge(TR)
        bl_label = MathTex("P(\\text{Sick} \\cap -)").to_edge(BL)
        br_label = MathTex("P(\\text{Not Sick} \\cap -)").to_edge(BR)

        # Initial counts
        tl_count = MathTex(f"{int(sick_and_positive)}").next_to(tl_label, DOWN)
        tr_count = MathTex(f"{int(not_sick_and_positive)}").next_to(tr_label, DOWN)
        bl_count = MathTex(f"{int(sick_and_negative)}").next_to(bl_label, DOWN)
        br_count = MathTex(f"{int(not_sick_and_negative)}").next_to(br_label, DOWN)

        # Group elements
        quadrants = VGroup(
            Rectangle(width=2, height=1.5, color=BLUE, fill_opacity=0.3).move([-2, 1.5]),
            Rectangle(width=2, height=1.5, color=GREEN, fill_opacity=0.3).move([0, 1.5]),
            Rectangle(width=2, height=1.5, color=RED, fill_opacity=0.3).move([-2, -1.5]),
            Rectangle(width=2, height=1.5, color=YELLOW, fill_opacity=0.3).move([0, -1.5])
        )

        labels_group = VGroup(tl_label, tr_label, bl_label, br_label)
        counts_group = VGroup(tl_count, tr_count, bl_count, br_count)

        self.play(Create(box), Write(labels_group))
        self.play(Create(quadrants), Write(counts_group))
        self.wait(1)

        # Highlight sick and positive
        highlight = SurroundingRectangle(quadrants[0], color=ORANGE, buff=0.1)
        self.play(Create(highlight))
        self.wait(0.5)
        self.play(FadeOut(highlight))

        # Bayes' theorem calculation
        bayes_formula = MathTex("P(\\text{Sick} | +) = \\frac{P(\\text{Sick} \\cap +)}{P(\\text{Sick} \\cap +) + P(\\text{Not Sick} \\cap +)}").to_edge(DOWN)
        self.play(Write(bayes_formula))
        self.wait(1)

        # Substitute values
        bayes_formula_substituted = MathTex(f"P(\\text{Sick} | +) = \\frac{{{int(sick_and_positive)}}}{{{int(sick_and_positive)} + {int(not_sick_and_positive)}}}").to_edge(DOWN)
        self.play(TransformMatchingTex(bayes_formula, bayes_formula_substituted))
        self.wait(1)

        # Calculate probability
        probability = sick_and_positive / (sick_and_positive + not_sick_and_positive)
        probability_text = MathTex(f"P(\\text{Sick} | +) \\approx {probability:.2f}").to_edge(DOWN)
        self.play(TransformMatchingTex(bayes_formula_substituted, probability_text))
        self.wait(2)

        # Paradox explanation
        paradox_text = Text("Despite 95% accuracy, low prevalence leads to a high false positive rate!", font_size=20).to_edge(DOWN)
        self.play(Write(paradox_text))
        self.wait(3)
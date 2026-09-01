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
        
        # Bayes Box
        box = Rectangle(width=4, height=3, color=WHITE)
        box.set_fill(color=GREY_A, opacity=0.5)

        # Quadrants
        q1 = Rectangle(width=2, height=1.5, color=BLUE_A, fill_opacity=0.2).move_to(box.get_center() + UP * 0.75 + LEFT * 1)
        q2 = Rectangle(width=2, height=1.5, color=RED_A, fill_opacity=0.2).move_to(box.get_center() + UP * 0.75 + RIGHT * 1)
        q3 = Rectangle(width=2, height=1.5, color=GREEN_A, fill_opacity=0.2).move_to(box.get_center() + DOWN * 0.75 + LEFT * 1)
        q4 = Rectangle(width=2, height=1.5, color=YELLOW_A, fill_opacity=0.2).move_to(box.get_center() + DOWN * 0.75 + RIGHT * 1)

        # Labels
        q1_label = MathTex("P(\\text{Sick} \\cap +)").move_to(q1.get_center())
        q2_label = MathTex("P(\\text{Not Sick} \\cap +)").move_to(q2.get_center())
        q3_label = MathTex("P(\\text{Sick} \\cap -)").move_to(q3.get_center())
        q4_label = MathTex("P(\\text{Not Sick} \\cap -)").move_to(q4.get_center())

        # Initial Counts
        q1_count = MathTex(f"{int(sick_and_positive)}").move_to(q1.get_center() + DOWN * 0.5)
        q2_count = MathTex(f"{int(not_sick_and_positive)}").move_to(q2.get_center() + DOWN * 0.5)
        q3_count = MathTex(f"{int(sick_and_negative)}").move_to(q3.get_center() + DOWN * 0.5)
        q4_count = MathTex(f"{int(not_sick_and_negative)}").move_to(q4.get_center() + DOWN * 0.5)

        # Highlight Sick and Positive
        highlight = SurroundingRectangle(q1, color=GREEN, buff=0.1)

        # Bayes' Theorem Calculation
        bayes_theorem = MathTex("P(\\text{Sick} | +) = \\frac{P(\\text{Sick} \\cap +)}{P(\\text{Sick} \\cap +) + P(\\text{Not Sick} \\cap +)}").move_to(DOWN * 2)
        bayes_theorem_calc = MathTex(f"\\approx \\frac{{{int(sick_and_positive)}}}{{{int(sick_and_positive)} + {int(not_sick_and_positive)}}}") .move_to(DOWN * 2 + DOWN * 0.5)
        probability = MathTex(f"\\approx {round(sick_and_positive / (sick_and_positive + not_sick_and_positive), 3)}").move_to(DOWN * 2 + DOWN * 1)

        # Paradox Explanation
        paradox_text = Text("Low prevalence + high accuracy ≠ high reliability", font_size=20).move_to(DOWN * 3)

        # Animation
        self.play(Create(box), Write(q1_label), Write(q2_label), Write(q3_label), Write(q4_label))
        self.play(Write(q1_count), Write(q2_count), Write(q3_count), Write(q4_count))
        self.wait(1)
        self.play(Create(highlight))
        self.wait(1)
        self.play(Write(bayes_theorem))
        self.wait(1)
        self.play(Write(bayes_theorem_calc))
        self.wait(1)
        self.play(Write(probability))
        self.wait(1)
        self.play(Write(paradox_text))
        self.wait(2)
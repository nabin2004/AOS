from manim import *

class BayesTheorem(Scene):
    def construct(self):
        # Parameters
        total_population = 1000
        sick_population = 1
        test_sensitivity = 0.95  # True positive rate
        test_specificity = 0.95  # True negative rate

        # Calculate counts
        sick_plus = sick_population * test_sensitivity
        sick_minus = sick_population * (1 - test_sensitivity)
        not_sick_plus = (total_population - sick_population) * (1 - test_specificity)
        not_sick_minus = (total_population - sick_population) * test_specificity

        # Create Bayes box
        box = Rectangle(width=4, height=3, color=WHITE)
        box.set_fill(opacity=0.1)

        # Quadrant labels
        tl_label = MathTex("P(\\text{Sick} \\cap +)").to_edge(TL)
        tr_label = MathTex("P(\\text{Not Sick} \\cap +)").to_edge(TR)
        bl_label = MathTex("P(\\text{Sick} \\cap -)").to_edge(BL)
        br_label = MathTex("P(\\text{Not Sick} \\cap -)").to_edge(BR)

        # Initial counts
        tl_count = MathTex(f"{round(sick_plus)}").next_to(tl_label, DOWN)
        tr_count = MathTex(f"{round(not_sick_plus)}").next_to(tr_label, DOWN)
        bl_count = MathTex(f"{round(sick_minus)}").next_to(bl_label, DOWN)
        br_count = MathTex(f"{round(not_sick_minus)}").next_to(br_label, DOWN)

        # Group elements
        quadrants = VGroup(
            Rectangle(width=2, height=1.5, color=BLUE).move_to(box.get_center() + UP * 0.75 + LEFT * 1),
            Rectangle(width=2, height=1.5, color=RED).move_to(box.get_center() + UP * 0.75 + RIGHT * 1),
            Rectangle(width=2, height=1.5, color=GREEN).move_to(box.get_center() + DOWN * 0.75 + LEFT * 1),
            Rectangle(width=2, height=1.5, color=YELLOW).move_to(box.get_center() + DOWN * 0.75 + RIGHT * 1)
        )

        counts = VGroup(tl_count, tr_count, bl_count, br_count)

        # Display initial setup
        self.play(Create(box), Write(tl_label), Write(tr_label), Write(bl_label), Write(br_label))
        self.play(Create(quadrants), Write(counts))
        self.wait(2)

        # Highlight sick +
        self.play(quadrants[0].animate.set_fill(opacity=1), run_time=1)
        self.wait(1)

        # Calculation
        calculation = MathTex("P(\\text{Sick} | +) = \\frac{P(\\text{Sick} \\cap +)}{P(\\text{Sick} \\cap +) + P(\\text{Not Sick} \\cap +)}").to_edge(DOWN)
        self.play(Write(calculation))
        self.wait(2)

        # Substitute values
        calculation_substituted = MathTex(f"P(\\text{Sick} | +) = \\frac{{{round(sick_plus)}}}{{{round(sick_plus)} + {round(not_sick_plus)}}}")\
            .move_to(calculation.get_center())
        self.play(Transform(calculation, calculation_substituted))
        self.wait(2)

        # Final probability
        final_probability = calculation_substituted.get_part_by_tex("P(\\text{Sick} | +)").get_text()
        final_probability_value = DecimalNumber(eval(final_probability)).move_to(calculation.get_center())
        self.play(Transform(calculation, final_probability_value))
        self.wait(1)

        # Paradox explanation
        paradox_text = Text("High false positive rate due to low disease prevalence.", font_size=24).to_edge(DOWN)
        self.play(Write(paradox_text))
        self.wait(3)
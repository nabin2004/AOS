from manim import *

class BayesTheorem(Scene):
    def construct(self):
        # Define the initial counts
        total_people = 1000
        sick_people = 1
        not_sick_people = total_people - sick_people
        test_positive = 0.95  # 95% accurate test
        test_negative = 0.05  # 5% false negative rate

        # Create the Bayes box
        bayes_box = VGroup()
        for i in range(2):
            for j in range(2):
                rect = Rectangle(width=4, height=4, color=WHITE)
                rect.shift(LEFT * (i - 1) * 6 + DOWN * (j - 1) * 6)
                bayes_box.add(rect)

        # Populate the Bayes box with initial counts
        bayes_box[0].set_fill(BLUE, 0.5)  # P(sick ∩ +)
        bayes_box[1].set_fill(RED, 0.5)  # P(not-sick ∩ +)
        bayes_box[2].set_fill(BLUE, 0.5)  # P(sick ∩ −)
        bayes_box[3].set_fill(RED, 0.5)  # P(not-sick ∩ −)

        # Animate the division
        self.play(
            AnimationGroup(
                bayes_box[0].animate.set_fill(BLUE, 0.5),
                bayes_box[1].animate.set_fill(RED, 0.5),
                bayes_box[2].animate.set_fill(BLUE, 0.5),
                bayes_box[3].animate.set_fill(RED, 0.5),
                rate_func=linear,
                run_time=2,
            )
        )

        # Highlight the sick population who tested +
        self.play(
            AnimationGroup(
                bayes_box[0].animate.set_fill(BLUE, 1),
                bayes_box[1].animate.set_fill(RED, 0.5),
                bayes_box[2].animate.set_fill(BLUE, 0.5),
                bayes_box[3].animate.set_fill(RED, 0.5),
                rate_func=linear,
                run_time=1,
            )
        )

        # Show final calculation
        self.play(
            AnimationGroup(
                bayes_box[0].animate.set_fill(BLUE, 0.5),
                bayes_box[1].animate.set_fill(RED, 0.5),
                bayes_box[2].animate.set_fill(BLUE, 0.5),
                bayes_box[3].animate.set_fill(RED, 0.5),
                rate_func=linear,
                run_time=1,
            )
        )

        # Display final probability
        final_probability = (sick_people * test_positive) / (sick_people * test_positive + not_sick_people * test_positive)
        probability_text = Text(f"P(sick | +) = {final_probability:.2f}").shift(UP * 2)
        self.play(Write(probability_text))

        # Explain the paradox
        paradox_text = Text("The test is 95% accurate, but the disease is rare, so most people who test positive are actually healthy!").shift(DOWN * 2)
        self.play(Write(paradox_text))
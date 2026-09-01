from manim import *

class BayesBox(Scene):
    def construct(self):
        # 1. Rectangle divided into four quadrants
        rect = Rectangle(width=4, height=3, color=WHITE, stroke_width=0.8)
        rect.shift(LEFT * 1.5)
        self.play(Create(rect))

        # Vertical and horizontal lines
        v_line = Line(rect.get_bottom(), rect.get_top(), color=WHITE, stroke_width=0.8)
        h_line = Line(rect.get_left(), rect.get_right(), color=WHITE, stroke_width=0.8)
        v_line.shift(rect.get_center() - UP * 1.5)
        h_line.shift(rect.get_center() - LEFT * 2)
        self.play(Create(v_line), Create(h_line))

        # 2. Labeling quadrants and initial counts
        sick_plus = Tex("Sick & +", color=YELLOW).scale(0.7).move_to(rect.get_top_left() + DOWN * 0.5 + LEFT * 0.5)
        sick_minus = Tex("Sick & -", color=YELLOW).scale(0.7).move_to(rect.get_bottom_left() + UP * 0.5 + LEFT * 0.5)
        healthy_plus = Tex("Healthy & +", color=YELLOW).scale(0.7).move_to(rect.get_top_right() + DOWN * 0.5 + RIGHT * 0.5)
        healthy_minus = Tex("Healthy & -", color=YELLOW).scale(0.7).move_to(rect.get_bottom_right() + UP * 0.5 + RIGHT * 0.5)

        self.play(Write(sick_plus), Write(sick_minus), Write(healthy_plus), Write(healthy_minus))

        # Initial counts
        sick_plus_count = Tex("1", color=GREEN).scale(0.6).next_to(sick_plus, DOWN)
        sick_minus_count = Tex("999", color=GREEN).scale(0.6).next_to(sick_minus, DOWN)
        healthy_plus_count = Tex("5", color=GREEN).scale(0.6).next_to(healthy_plus, DOWN)
        healthy_minus_count = Tex("995", color=GREEN).scale(0.6).next_to(healthy_minus, DOWN)

        self.play(Write(sick_plus_count), Write(sick_minus_count), Write(healthy_plus_count), Write(healthy_minus_count))

        # 3. Animate the division (filling quadrants)
        self.play(
            Fill(rect.get_submobject(rect.get_top_left()), color=YELLOW, opacity=0.5),
            Fill(rect.get_submobject(rect.get_bottom_left()), color=YELLOW, opacity=0.5),
            Fill(rect.get_submobject(rect.get_top_right()), color=YELLOW, opacity=0.5),
            Fill(rect.get_submobject(rect.get_bottom_right()), color=YELLOW, opacity=0.5)
        )

        # 4. Highlight sick population who tested +
        self.play(Indicate(sick_plus, color=RED))

        # 5. Show Bayes calculation
        bayes_formula = Tex("P(Sick | +) = P(Sick \\cap +) / P(+)", color=BLUE).scale(0.8).to_edge(UP)
        self.play(Write(bayes_formula))

        p_sick_cap_plus = Tex("P(Sick \\cap +) = 1 / 1000", color=BLUE).scale(0.6).next_to(bayes_formula, DOWN)
        p_plus = Tex("P(+) = (1 + 5) / 1000 = 6 / 1000", color=BLUE).scale(0.6).next_to(p_sick_cap_plus, DOWN)
        self.play(Write(p_sick_cap_plus), Write(p_plus))

        final_prob = Tex("P(Sick | +) = 1 / 6 \\approx 0.167", color=RED).scale(0.8).next_to(p_plus, DOWN)
        self.play(Write(final_prob))

        # 6. Display final probability and explain paradox
        paradox_text = Tex("Despite 95% test accuracy, only ~17% are actually sick!", color=RED).scale(0.6).next_to(final_prob, DOWN)
        self.play(Write(paradox_text))

        self.wait(3)
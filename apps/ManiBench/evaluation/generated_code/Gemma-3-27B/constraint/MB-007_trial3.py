from manim import *

class BayesBox(Scene):
    def construct(self):
        # Initial setup
        rect = Rectangle(width=4, height=3, stroke_width=0.8, stroke_color=BLACK, fill_opacity=0.1, critical=True)
        self.play(Create(rect))
        self.wait(1)

        # Divide into quadrants
        line_v = Line(rect.get_bottom_left() + UP * 3, rect.get_bottom_right() + UP * 3, stroke_width=0.8, stroke_color=BLACK, critical=True)
        line_h = Line(rect.get_bottom_left() + RIGHT * 2, rect.get_top_left() + RIGHT * 2, stroke_width=0.8, stroke_color=BLACK, critical=True)
        self.play(Create(line_v), Create(line_h))
        self.wait(1)

        # Labels and initial counts
        sick_plus_label = Tex("Sick & +", font_size=24).move_to(rect.get_top_left() + DOWN * 0.5 + LEFT * 0.5)
        sick_minus_label = Tex("Sick & -", font_size=24).move_to(rect.get_bottom_left() + UP * 0.5 + LEFT * 0.5)
        healthy_plus_label = Tex("Healthy & +", font_size=24).move_to(rect.get_top_right() + DOWN * 0.5 + RIGHT * 0.5)
        healthy_minus_label = Tex("Healthy & -", font_size=24).move_to(rect.get_bottom_right() + UP * 0.5 + RIGHT * 0.5)

        sick_plus_count = Tex("1", font_size=24).next_to(sick_plus_label, DOWN)
        sick_minus_count = Tex("999", font_size=24).next_to(sick_minus_label, DOWN)
        healthy_plus_count = Tex("49", font_size=24).next_to(healthy_plus_label, DOWN)
        healthy_minus_count = Tex("950", font_size=24).next_to(healthy_minus_label, DOWN)

        self.play(Write(sick_plus_label), Write(sick_minus_label), Write(healthy_plus_label), Write(healthy_minus_label))
        self.play(Write(sick_plus_count), Write(sick_minus_count), Write(healthy_plus_count), Write(healthy_minus_count))
        self.wait(2)

        # Animate populations (simple fill for now)
        sick_plus_rect = Rectangle(width=1, height=0.5, fill_color=BLUE, fill_opacity=0.5).move_to(rect.get_top_left() + DOWN * 0.5 + LEFT * 0.5)
        sick_minus_rect = Rectangle(width=1, height=0.5, fill_color=BLUE, fill_opacity=0.5).move_to(rect.get_bottom_left() + UP * 0.5 + LEFT * 0.5)
        healthy_plus_rect = Rectangle(width=1, height=0.5, fill_color=BLUE, fill_opacity=0.5).move_to(rect.get_top_right() + DOWN * 0.5 + RIGHT * 0.5)
        healthy_minus_rect = Rectangle(width=1, height=0.5, fill_color=BLUE, fill_opacity=0.5).move_to(rect.get_bottom_right() + UP * 0.5 + RIGHT * 0.5)

        self.play(Create(sick_plus_rect), Create(sick_minus_rect), Create(healthy_plus_rect), Create(healthy_minus_rect))
        self.wait(1)

        # Highlight sick population who tested +
        box = SurroundingRectangle(sick_plus_rect, color=YELLOW, buff=0.2)
        self.play(Create(box))
        self.wait(1)
        self.play(Uncreate(box))

        # Bayes calculation
        bayes_formula = Tex("P(Sick | +) = P(Sick \\cap +) / P(+)", font_size=36).to_edge(UP)
        self.play(Write(bayes_formula))
        self.wait(1)

        p_sick_cap_plus = Tex("P(Sick \\cap +) = 1 / 1000 = 0.001", font_size=24).next_to(bayes_formula, DOWN)
        p_plus = Tex("P(+) = (1 + 49) / 1000 = 0.05", font_size=24).next_to(p_sick_cap_plus, DOWN)
        self.play(Write(p_sick_cap_plus), Write(p_plus))
        self.wait(1)

        final_prob = Tex("P(Sick | +) = 0.001 / 0.05 = 0.019 = 1.9%", font_size=36).next_to(p_plus, DOWN)
        self.play(Write(final_prob))
        self.wait(2)

        # Paradox explanation
        paradox_text = Tex("Despite 95% test accuracy, only 1.9% are actually sick!", font_size=24).to_edge(DOWN)
        self.play(Write(paradox_text))
        self.wait(3)
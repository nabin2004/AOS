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
        highlight_rect = Rectangle(width=1, height=0.5, stroke_width=3, stroke_color=RED, fill_color=RED, fill_opacity=0.2).move_to(rect.get_top_left() + DOWN * 0.5 + LEFT * 0.5)
        self.play(Create(highlight_rect))
        self.wait(2)

        # Bayes calculation
        bayes_formula = Tex("P(Sick | +) = P(Sick \\cap +) / P(+)", font_size=36).to_edge(UP)
        self.play(Write(bayes_formula))
        self.wait(1)

        substitution = Tex("= 1 / (1 + 49)", font_size=36).next_to(bayes_formula, DOWN)
        self.play(Write(substitution))
        self.wait(1)

        result = Tex("= 0.0196", font_size=36).next_to(substitution, DOWN)
        self.play(Write(result))
        self.wait(2)

        # Final probability and paradox
        paradox_text = Tex("Despite 95% test accuracy, only ~1.9% are actually sick!", font_size=24).to_edge(DOWN)
        self.play(Write(paradox_text))
        self.wait(3)
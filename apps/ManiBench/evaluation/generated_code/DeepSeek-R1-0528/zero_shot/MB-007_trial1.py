from manim import *

class BayesBox(Scene):
    def construct(self):
        # Create title
        title = Text("Bayes' Theorem Visualization", font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # Create main rectangle
        box = Rectangle(width=6, height=4, color=WHITE)
        box.shift(DOWN*0.5)

        # Add dividing lines
        h_line = Line(box.get_left(), box.get_right())
        v_line = Line(box.get_top(), box.get_bottom())
        self.play(Create(box), Create(h_line), Create(v_line))
        self.wait(1)

        # Add quadrant labels
        sick_plus = Text("Sick ∩ +", font_size=24).move_to(box.get_corner(UL) + [0.7, -0.5, 0])
        notsick_plus = Text("Not Sick ∩ +", font_size=24).move_to(box.get_corner(UR) + [-0.7, -0.5, 0])
        sick_minus = Text("Sick ∩ -", font_size=24).move_to(box.get_corner(DL) + [0.7, 0.5, 0])
        notsick_minus = Text("Not Sick ∩ -", font_size=24).move_to(box.get_corner(DR) + [-0.7, 0.5, 0])
        
        self.play(
            Write(sick_plus),
            Write(notsick_plus),
            Write(sick_minus),
            Write(notsick_minus)
        )
        self.wait(1)

        # Population information
        pop_text = Text("Population: 1000 people", font_size=24).next_to(box, DOWN, buff=0.5)
        sick_text = Text("Sick: 1 person", font_size=24).next_to(pop_text, DOWN, buff=0.2)
        not_sick_text = Text("Not Sick: 999 people", font_size=24).next_to(sick_text, DOWN, buff=0.2)
        
        self.play(Write(pop_text))
        self.wait(0.5)
        self.play(Write(sick_text))
        self.play(Write(not_sick_text))
        self.wait(1)

        # Test accuracy
        accuracy = Text("Test Accuracy: 95%", font_size=24).next_to(not_sick_text, DOWN, buff=0.5)
        self.play(Write(accuracy))
        self.wait(1)

        # Animate counts in quadrants
        tp_count = Text("0.95", font_size=28, color=YELLOW).move_to(box.get_corner(UL) + [1, -1, 0])
        fp_count = Text("49.95", font_size=28).move_to(box.get_corner(UR) + [-1, -1, 0])
        fn_count = Text("0.05", font_size=28).move_to(box.get_corner(DL) + [1, 1, 0])
        tn_count = Text("949.05", font_size=28).move_to(box.get_corner(DR) + [-1, 1, 0])
        
        self.play(
            FadeIn(tp_count),
            FadeIn(fp_count),
            FadeIn(fn_count),
            FadeIn(tn_count)
        )
        self.wait(2)

        # Highlight true positive quadrant
        tp_highlight = SurroundingRectangle(tp_count, color=YELLOW, buff=0.2)
        self.play(Create(tp_highlight))
        self.wait(1)

        # Highlight positive tests column
        pos_column_highlight = Rectangle(
            width=box.width/2, height=box.height,
            stroke_color=GREEN, fill_color=GREEN, 
            fill_opacity=0.2
        ).move_to(box.get_top() + [box.width/4, -box.height/2, 0])
        
        self.play(Transform(tp_highlight, pos_column_highlight))
        self.wait(1)
        self.play(FadeOut(tp_highlight))

        # Calculate probability
        formula = MathTex(
            r"P(\text{sick} \mid +) = \frac{P(\text{sick} \cap +)}{P(+)} = \frac{0.95}{0.95 + 49.95} = \frac{0.95}{50.9} \approx 0.0187",
            font_size=36
        ).next_to(box, DOWN, buff=1.2)
        
        self.play(Write(formula))
        self.wait(2)

        # Explain paradox
        paradox = Text(
            "Paradox: Despite 95% test accuracy, P(sick|+) is only ~1.87%\n"
            "because false positives dominate when disease prevalence is low",
            font_size=24, color=RED
        ).next_to(formula, DOWN, buff=0.7)
        
        self.play(Write(paradox))
        self.wait(3)

        # Final probability display
        result = MathTex(r"P(\text{sick} \mid +) \approx 1.87\%", font_size=42, color=YELLOW)
        result_box = SurroundingRectangle(result, color=YELLOW, buff=0.3)
        result_group = VGroup(result, result_box).next_to(paradox, DOWN, buff=0.8)
        
        self.play(Create(result_group))
        self.wait(3)
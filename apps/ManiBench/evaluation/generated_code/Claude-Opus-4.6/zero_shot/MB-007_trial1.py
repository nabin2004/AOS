from manim import *

class BayesBoxVisualization(Scene):
    def construct(self):
        # Title
        title = Text("Bayes' Theorem: The False Positive Paradox", font_size=36)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(0.5)

        # Setup parameters
        # Population: 1000, Prevalence: 1/1000, Test accuracy: 95% sensitivity, 95% specificity
        total = 1000
        sick = 1
        not_sick = 999
        sensitivity = 0.95  # P(+|sick)
        specificity = 0.95  # P(-|not sick)

        sick_pos = round(sick * sensitivity)    # 1 * 0.95 ≈ 1
        sick_neg = sick - sick_pos               # 0
        not_sick_pos = round(not_sick * (1 - specificity))  # 999 * 0.05 ≈ 50
        not_sick_neg = not_sick - not_sick_pos    # 949

        # Step 1: Show the setup
        setup_text = VGroup(
            Text("Population: 1,000 people", font_size=28),
            Text("Disease prevalence: 1 in 1,000", font_size=28),
            Text("Test sensitivity: 95% (detects sick correctly)", font_size=28),
            Text("Test specificity: 95% (detects healthy correctly)", font_size=28),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        setup_text.next_to(title, DOWN, buff=0.4)

        for line in setup_text:
            self.play(FadeIn(line, shift=RIGHT), run_time=0.6)
        self.wait(1.5)

        self.play(FadeOut(setup_text))
        self.wait(0.3)

        # Step 2: Create the Bayes Box
        box_width = 8
        box_height = 4
        box_center = DOWN * 0.3

        # The vertical divider position represents proportion of sick vs not sick
        # Since 1/1000 is very small, we'll exaggerate for visibility
        sick_frac_visual = 0.15  # Exaggerated for visibility
        pos_frac_visual_sick = 0.7  # Visual proportion for + among sick
        pos_frac_visual_notsick = 0.35  # Visual proportion for + among not sick

        # Outer rectangle
        outer_rect = Rectangle(
            width=box_width, height=box_height,
            stroke_color=WHITE, stroke_width=3
        ).move_to(box_center)

        self.play(Create(outer_rect))
        self.wait(0.3)

        # Vertical divider (sick | not sick)
        vert_x = outer_rect.get_left()[0] + box_width * sick_frac_visual
        vert_line = Line(
            start=[vert_x, outer_rect.get_top()[1], 0],
            end=[vert_x, outer_rect.get_bottom()[1], 0],
            stroke_color=YELLOW, stroke_width=3
        )

        sick_label = Text("Sick", font_size=24, color=RED)
        sick_label.next_to(
            [outer_rect.get_left()[0] + box_width * sick_frac_visual / 2, outer_rect.get_bottom()[1], 0],
            DOWN, buff=0.2
        )
        not_sick_label = Text("Not Sick", font_size=24, color=GREEN)
        not_sick_label.next_to(
            [vert_x + (box_width * (1 - sick_frac_visual)) / 2, outer_rect.get_bottom()[1], 0],
            DOWN, buff=0.2
        )

        self.play(Create(vert_line), Write(sick_label), Write(not_sick_label))
        self.wait(0.5)

        # Column count labels
        sick_count = Text(f"{sick}", font_size=22, color=RED)
        sick_count.next_to(sick_label, DOWN, buff=0.1)
        not_sick_count = Text(f"{not_sick}", font_size=22, color=GREEN)
        not_sick_count.next_to(not_sick_label, DOWN, buff=0.1)

        self.play(Write(sick_count), Write(not_sick_count))
        self.wait(0.5)

        # Horizontal divider (test + | test -)
        horiz_y = outer_rect.get_bottom()[1] + box_height * 0.55
        horiz_line = Line(
            start=[outer_rect.get_left()[0], horiz_y, 0],
            end=[outer_rect.get_right()[0], horiz_y, 0],
            stroke_color=BLUE, stroke_width=3
        )

        test_pos_label = Text("Test +", font_size=24, color=BLUE)
        test_pos_label.next_to(
            [outer_rect.get_left()[0], (horiz_y + outer_rect.get_top()[1]) / 2, 0],
            LEFT, buff=0.2
        )
        test_neg_label = Text("Test −", font_size=24, color=GREY)
        test_neg_label.next_to(
            [outer_rect.get_left()[0], (outer_rect.get_bottom()[1] + horiz_y) / 2, 0],
            LEFT, buff=0.2
        )

        self.play(Create(horiz_line), Write(test_pos_label), Write(test_neg_label))
        self.wait(0.5)

        # Step 3: Fill in the four quadrants with counts
        # Quadrant centers
        left_center_x = (outer_rect.get_left()[0] + vert_x) / 2
        right_center_x = (vert_x + outer_rect.get_right()[0]) / 2
        top_center_y = (horiz_y + outer_rect.get_top()[1]) / 2
        bottom_center_y = (outer_rect.get_bottom()[1] + horiz_y) / 2

        # Top-left: Sick ∩ Test+ (True Positive)
        tl_rect = Rectangle(
            width=vert_x - outer_rect.get_left()[0],
            height=outer_rect.get_top()[1] - horiz_y,
            fill_color=RED, fill_opacity=0.3,
            stroke_width=0
        ).move_to([left_center_x, top_center_y, 0])

        tl_text = VGroup(
            Text("True +", font_size=18, color=RED),
            Text(f"{sick_pos}", font_size=28, color=RED, weight=BOLD),
        ).arrange(DOWN, buff=0.05).move_to([left_center_x, top_center_y, 0])

        # Top-right: Not Sick ∩ Test+ (False Positive)
        tr_rect = Rectangle(
            width=outer_rect.get_right()[0] - vert_x,
            height=outer_rect.get_top()[1] - horiz_y,
            fill_color=ORANGE, fill_opacity=0.2,
            stroke_width=0
        ).move_to([right_center_x, top_center_y, 0])

        tr_text = VGroup(
            Text("False +", font_size=18, color=ORANGE),
            Text(f"{not_sick_pos}", font_size=28, color=ORANGE, weight=BOLD),
        ).arrange(DOWN, buff=0.05).move_to([right_center_x, top_center_y, 0])

        # Bottom-left: Sick ∩ Test- (False Negative)
        bl_rect = Rectangle(
            width=vert_x - outer_rect.get_left()[0],
            height=horiz_y - outer_rect.get_bottom()[1],
            fill_color=PURPLE, fill_opacity=0.2,
            stroke_width=0
        ).move_to([left_center_x, bottom_center_y, 0])

        bl_text = VGroup(
            Text("False −", font_size=18, color=PURPLE),
            Text(f"{sick_neg}", font_size=28, color=PURPLE, weight=BOLD),
        ).arrange(DOWN, buff=0.05).move_to([left_center_x, bottom_center_y, 0])

        # Bottom-right: Not Sick ∩ Test- (True Negative)
        br_rect = Rectangle(
            width=outer_rect.get_right()[0] - vert_x,
            height=horiz_y - outer_rect.get_bottom()[1],
            fill_color=GREEN, fill_opacity=0.2,
            stroke_width=0
        ).move_to([right_center_x, bottom_center_y, 0])

        br_text = VGroup(
            Text("True −", font_size=18, color=GREEN),
            Text(f"{not_sick_neg}", font_size=28, color=GREEN, weight=BOLD),
        ).arrange(DOWN, buff=0.05).move_to([right_center_x, bottom_center_y, 0])

        # Animate filling quadrants
        self.play(FadeIn(tl_rect), Write(tl_text), run_time=0.8)
        self.play(FadeIn(tr_rect), Write(tr_text), run_time=0.8)
        self.play(FadeIn(bl_rect), Write(bl_text), run_time=0.8)
        self.play(FadeIn(br_rect), Write(br_text), run_time=0.8)
        self.wait(1)

        # Step 4: Show total who tested positive
        total_pos = sick_pos + not_sick_pos
        total_pos_text = Text(
            f"Total who tested positive: {sick_pos} + {not_sick_pos} = {total_pos}",
            font_size=26, color=BLUE
        )
        total_pos_text.next_to(outer_rect, RIGHT, buff=0.3).shift(UP * 1)

        # Highlight the top row
        top_highlight = Rectangle(
            width=box_width,
            height=outer_rect.get_top()[1] - horiz_y,
            stroke_color=BLUE, stroke_width=4,
            fill_opacity=0
        ).move_to([(outer_rect.get_left()[0] + outer_rect.get_right()[0]) / 2, top_center_y, 0])

        self.play(Create(top_highlight), run_time=0.8)
        self.play(Write(total_pos_text), run_time=1)
        self.wait(1)

        # Step 5: Highlight the true positive (top-left)
        tl_highlight = Rectangle(
            width=vert_x - outer_rect.get_left()[0],
            height=outer_rect.get_top()[1] - horiz_y,
            stroke_color=RED, stroke_width=5,
            fill_color=RED, fill_opacity=0.4
        ).move_to([left_center_x, top_center_y, 0])

        highlight_text = Text(
            f"Actually sick AND tested +: {sick_pos}",
            font_size=26, color=RED
        )
        highlight_text.next_to(total_pos_text, DOWN, buff=0.3)

        self.play(FadeIn(tl_highlight), run_time=0.8)
        self.play(Write(highlight_text), run_time=1)
        self.wait(1)

        # Step 6: Show the Bayes calculation
        self.play(
            FadeOut(top_highlight),
            FadeOut(tl_highlight),
            FadeOut(total_pos_text),
            FadeOut(highlight_text),
        )

        # Move the box to the left
        box_group = VGroup(
            outer_rect, vert_line, horiz_line,
            sick_label, not_sick_label, sick_count, not_sick_count,
            test_pos_label, test_neg_label,
            tl_rect, tl_text, tr_rect, tr_text,
            bl_rect, bl_text, br_rect, br_text,
        )

        self.play(box_group.animate.scale(0.65).to_edge(LEFT, buff=0.3).shift(DOWN * 0.2), run_time=1)
        self.wait(0.3)

        # Calculation on the right
        calc_title = Text("Bayes' Theorem Calculation:", font_size=28, color=YELLOW)
        calc_title.to_edge(RIGHT, buff=0.5).shift(UP * 1.8)

        formula = MathTex(
            r"P(\text{Sick} \mid +) = \frac{P(\text{Sick} \cap +)}{P(+)}",
            font_size=34
        )
        formula.next_to(calc_title, DOWN, buff=0.3)

        numbers = MathTex(
            r"= \frac{" + str(sick_pos) + r"}{" + str(sick_pos) + r" + " + str(not_sick_pos) + r"}",
            font_size=34
        )
        numbers.next_to(formula, DOWN, buff=0.3)

        prob_value = sick_pos / total_pos
        result = MathTex(
            r"= \frac{" + str(sick_pos) + r"}{" + str(total_pos) + r"} \approx " + f"{prob_value:.1%}".replace("%", r"\%"),
            font_size=34,
            color=YELLOW
        )
        result.next_to(numbers, DOWN, buff=0.3)

        self.play(Write(calc_title), run_time=0.8)
        self.play(Write(formula), run_time=1)
        self.wait(0.5)
        self.play(Write(numbers), run_time=1)
        self.wait(0.5)
        self.play(Write(result), run_time=1)
        self.wait(1)

        # Big result box
        result_box = SurroundingRectangle(result, color=YELLOW, buff=0.15, stroke_width=3)
        self.play(Create(result_box))
        self.wait(1)

        # Step 7: Explain the paradox
        paradox_title = Text("The Paradox:", font_size=28, color=RED_B)
        paradox_title.next_to(result_box, DOWN, buff=0.4)

        paradox_lines = VGroup(
            Text("• Test is 95% accurate", font_size=22),
            Text("• But if you test positive,", font_size=22),
            Text(f"  only ~{prob_value:.1%} chance you're sick!", font_size=22, color=RED),
            Text("", font_size=14),
            Text("Why? Disease is so rare (1 in 1000)", font_size=22, color=BLUE_B),
            Text("that false positives vastly", font_size=22, color=BLUE_B),
            Text("outnumber true positives.", font_size=22, color=BLUE_B),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        paradox_lines.next_to(paradox_title, DOWN, buff=0.2, aligned_edge=LEFT)

        self.play(Write(paradox_title), run_time=0.8)
        for line in paradox_lines:
            self.play(FadeIn(line, shift=RIGHT * 0.3), run_time=0.5)
        self.wait(1)

        # Final emphasis
        final_msg = Text(
            f"50 false positives vs {sick_pos} true positive!",
            font_size=30, color=YELLOW
        )
        final_box = SurroundingRectangle(final_msg, color=YELLOW, buff=0.15, stroke_width=3)
        final_group = VGroup(final_msg, final_box)
        final_group.to_edge(DOWN, buff=0.3)

        self.play(Write(final_msg), Create(final_box), run_time=1)
        self.wait(3)
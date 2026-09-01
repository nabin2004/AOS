from manim import *

class BayesBoxAnimation(Scene):
    def construct(self):
        # Configuration
        box_width = 6
        box_height = 4
        prevalence = 0.001  # 1 in 1000
        sensitivity = 0.95   # P(+|sick)
        specificity = 0.95   # P(-|healthy)
        
        # Title
        title = Text("Bayes' Theorem: The Bayes Box Visualization", font_size=40)
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))
        self.wait(0.5)
        
        # Create main box
        box = Rectangle(width=box_width, height=box_height, color=WHITE)
        box.move_to(ORIGIN)
        
        # Initial divider lines (centered, will move)
        h_line = Line(box.get_left(), box.get_right(), color=YELLOW)
        v_line = Line(box.get_top(), box.get_bottom(), color=YELLOW)
        
        self.play(Create(box))
        self.play(Create(h_line), Create(v_line))
        self.wait(0.5)
        
        # Labels
        sick_label = Text("Sick", color=RED, font_size=32).next_to(box, LEFT).shift(UP*box_height/4)
        healthy_label = Text("Not Sick", color=GREEN, font_size=32).next_to(box, LEFT).shift(DOWN*box_height/4)
        
        pos_label = Text("Test +", color=BLUE, font_size=32).next_to(box, UP).shift(LEFT*box_width/4)
        neg_label = Text("Test -", color=GRAY, font_size=32).next_to(box, UP).shift(RIGHT*box_width/4)
        
        self.play(
            Write(sick_label), 
            Write(healthy_label),
            Write(pos_label),
            Write(neg_label)
        )
        
        # Step 1: Show population and prevalence
        pop_text = MathTex(r"1000 \text{ people}", font_size=36).next_to(box, UP, buff=1.5)
        self.play(Write(pop_text))
        self.wait(0.5)
        
        # Animate horizontal split for prevalence (Sick vs Not Sick)
        # Sick row height: 0.1% of box_height
        sick_height = box_height * prevalence
        healthy_height = box_height * (1 - prevalence)
        
        new_y = box.get_top()[1] - sick_height
        new_h_line = Line(
            box.get_left(),
            box.get_right(),
            color=YELLOW
        ).move_to([0, new_y, 0])
        
        self.play(
            Transform(h_line, new_h_line),
            run_time=2
        )
        
        # Add counts for rows
        sick_count = MathTex("1", color=RED).scale(0.8)
        sick_count.move_to([box.get_left()[0] - 0.8, (box.get_top()[1] + new_y)/2, 0])
        
        healthy_count = MathTex("999", color=GREEN).scale(0.8)
        healthy_count.move_to([box.get_left()[0] - 0.8, (new_y + box.get_bottom()[1])/2, 0])
        
        self.play(Write(sick_count), Write(healthy_count))
        self.wait(0.5)
        
        # Step 2: Vertical splits for test accuracy
        # Top row (Sick): 95% Positive (left), 5% Negative (right)
        # Bottom row (Not Sick): 5% Positive (left), 95% Negative (right)
        
        sick_pos_width = box_width * sensitivity  # 95%
        healthy_pos_width = box_width * (1 - specificity)  # 5%
        
        # Remove single vertical line, create two segments
        self.play(FadeOut(v_line))
        
        v_line_top = Line(
            [box.get_left()[0], new_y, 0],
            box.get_top(),
            color=YELLOW
        )
        v_line_top.shift(RIGHT * (sick_pos_width - box_width/2))
        
        v_line_bottom = Line(
            box.get_bottom(),
            [box.get_left()[0], new_y, 0],
            color=YELLOW
        )
        v_line_bottom.shift(RIGHT * (healthy_pos_width - box_width/2))
        
        self.play(
            Create(v_line_top),
            Create(v_line_bottom),
            run_time=2
        )
        
        # Step 3: Fill in the quadrants with numbers
        # Quadrant centers
        tl_center = [box.get_left()[0] + sick_pos_width/2, (box.get_top()[1] + new_y)/2, 0]  # Sick & +
        tr_center = [box.get_left()[0] + sick_pos_width + (box_width - sick_pos_width)/2, (box.get_top()[1] + new_y)/2, 0]  # Sick & -
        bl_center = [box.get_left()[0] + healthy_pos_width/2, (new_y + box.get_bottom()[1])/2, 0]  # Not Sick & +
        br_center = [box.get_left()[0] + healthy_pos_width + (box_width - healthy_pos_width)/2, (new_y + box.get_bottom()[1])/2, 0]  # Not Sick & -
        
        tl_text = MathTex("0.95", color=YELLOW, font_size=28).move_to(tl_center)
        tr_text = MathTex("0.05", color=GRAY, font_size=24).move_to(tr_center)
        bl_text = MathTex("49.95", color=YELLOW, font_size=28).move_to(bl_center)
        br_text = MathTex("949.05", color=GRAY, font_size=28).move_to(br_center)
        
        # Animate numbers appearing
        self.play(
            Write(tl_text),
            Write(tr_text),
            Write(bl_text),
            Write(br_text),
            run_time=2
        )
        self.wait(0.5)
        
        # Step 4: Highlight Test Positive column (left side)
        highlight_left = SurroundingRectangle(
            VGroup(tl_text, bl_text),
            buff=0.2,
            color=BLUE,
            stroke_width=3
        )
        
        self.play(Create(highlight_left))
        self.wait(0.5)
        
        # Step 5: Highlight True Positives specifically
        highlight_tl = Rectangle(
            width=sick_pos_width,
            height=sick_height,
            fill_color=RED,
            fill_opacity=0.3,
            stroke_width=2,
            stroke_color=RED
        ).move_to(tl_center)
        
        self.play(FadeIn(highlight_tl))
        self.wait(0.5)
        
        # Add braces to show the calculation
        brace_top = Brace(
            Line([tl_center[0], tl_center[1], 0], [tr_center[0], tr_center[1], 0]),
            direction=UP,
            color=BLUE
        )
        brace_label = MathTex(r"\text{All Positive Tests}", font_size=24).next_to(brace_top, UP)
        
        self.play(
            GrowFromCenter(brace_top),
            Write(brace_label)
        )
        self.wait(0.5)
        
        # Step 6: Show the formula and calculation
        formula_group = VGroup()
        
        formula_title = Text("Bayes' Theorem:", font_size=32, color=WHITE)
        formula_title.to_edge(DOWN, buff=2.5)
        
        formula = MathTex(
            r"P(\text{Sick} | +) = \frac{P(\text{Sick} \cap +)}{P(+)}",
            r" = \frac{0.95}{0.95 + 49.95}",
            r" = \frac{0.95}{50.9}",
            r" \approx 0.019",
            font_size=34
        ).next_to(formula_title, DOWN)
        
        result_text = Text("≈ 1.9%", font_size=48, color=YELLOW, weight=BOLD)
        result_text.next_to(formula, DOWN, buff=0.5)
        
        self.play(
            Write(formula_title),
            run_time=1
        )
        self.play(
            Write(formula[0]),
            run_time=1
        )
        self.play(
            Write(formula[1]),
            run_time=1
        )
        self.play(
            Write(formula[2:]),
            run_time=1
        )
        self.play(
            TransformFromCopy(tl_text, result_text),
            run_time=1.5
        )
        
        self.wait(1)
        
        # Step 7: The Paradox explanation
        self.play(
            FadeOut(formula_title),
            FadeOut(formula),
            FadeOut(result_text),
            FadeOut(brace_top),
            FadeOut(brace_label),
            FadeOut(highlight_left),
            FadeOut(highlight_tl)
        )
        
        paradox_text = VGroup(
            Text("The Paradox:", font_size=36, color=RED, weight=BOLD),
            Text("Test is 95% accurate...", font_size=28),
            Text("But P(Sick | +) ≈ 2%", font_size=32, color=YELLOW),
            Text("False positives (49.95) overwhelm true positives (0.95)", font_size=26),
            Text("Low prevalence (0.1%) + High accuracy ≠ High precision", font_size=26)
        ).arrange(DOWN, buff=0.4).to_edge(DOWN, buff=1)
        
        # Arrow pointing to the false positive cell
        arrow_fp = Arrow(
            paradox_text[3].get_top(),
            bl_text.get_bottom(),
            color=YELLOW,
            buff=0.3
        )
        
        self.play(Write(paradox_text[0]))
        self.wait(0.5)
        self.play(Write(paradox_text[1]))
        self.wait(0.5)
        self.play(Write(paradox_text[2]))
        self.wait(0.5)
        self.play(
            Write(paradox_text[3]),
            Create(arrow_fp)
        )
        self.wait(0.5)
        self.play(Write(paradox_text[4]))
        
        # Final highlight of the ratio
        self.play(
            tl_text.animate.scale(1.5).set_color(RED),
            bl_text.animate.scale(1.2),
            run_time=2
        )
        
        self.wait(3)
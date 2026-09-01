from manim import *

class BayesBoxVisualization(Scene):
    def construct(self):
        # Configuration
        total_population = 1000
        prevalence = 0.001  # 1 in 1000
        sensitivity = 0.95  # True Positive Rate
        specificity = 0.95  # True Negative Rate
        
        # Calculate counts
        sick_count = int(total_population * prevalence)
        healthy_count = total_population - sick_count
        
        tp = int(sick_count * sensitivity)      # True Positives (Sick & +)
        fn = sick_count - tp                    # False Negatives (Sick & -)
        fp = int(healthy_count * (1 - specificity)) # False Positives (Healthy & +)
        tn = healthy_count - fp                 # True Negatives (Healthy & -)
        
        # Ensure at least 1 for visualization purposes if math rounds to 0
        if tp == 0: tp = 1 
        if fp == 0: fp = int(healthy_count * 0.05) # Force approx 5% false positive rate

        # --- 1. Create the Bayes Box Layout ---
        box_width = 8
        box_height = 5
        box = Rectangle(width=box_width, height=box_height, color=WHITE)
        box.move_to(ORIGIN)
        
        # Dividing lines
        h_line = Line(box.get_left(), box.get_right()).move_to(box.get_center())
        v_line = Line(box.get_top(), box.get_bottom()).move_to(box.get_center())
        
        # Quadrant Rectangles (for coloring)
        # Top-Left: Sick & +
        tl_rect = Rectangle(
            width=box_width/2, height=box_height/2, 
            fill_color=RED, fill_opacity=0.3, stroke_width=0
        ).align_to(box, UL)
        
        # Top-Right: Healthy & +
        tr_rect = Rectangle(
            width=box_width/2, height=box_height/2, 
            fill_color=BLUE, fill_opacity=0.3, stroke_width=0
        ).align_to(box, UR)
        
        # Bottom-Left: Sick & -
        bl_rect = Rectangle(
            width=box_width/2, height=box_height/2, 
            fill_color=RED, fill_opacity=0.1, stroke_width=0
        ).align_to(box, DL)
        
        # Bottom-Right: Healthy & -
        br_rect = Rectangle(
            width=box_width/2, height=box_height/2, 
            fill_color=BLUE, fill_opacity=0.1, stroke_width=0
        ).align_to(box, DR)

        # Labels for Quadrants
        tl_label = Text(f"Sick & +\n({tp})", font_size=24).move_to(tl_rect.get_center())
        tr_label = Text(f"Not Sick & +\n({fp})", font_size=24).move_to(tr_rect.get_center())
        bl_label = Text(f"Sick & -\n({fn})", font_size=24).move_to(bl_rect.get_center())
        br_label = Text(f"Not Sick & -\n({tn})", font_size=24).move_to(br_rect.get_center())

        # Axis Labels
        row_label_left = Text("Sick", font_size=28).next_to(box, LEFT, buff=0.5)
        row_label_right = Text("Not Sick", font_size=28).next_to(box, RIGHT, buff=0.5) # Actually centered on rows usually, but let's do top/bottom
        # Let's redo row/col labels for clarity
        col_label_top = Text("Test Positive (+)", font_size=24).next_to(box, UP, buff=0.3)
        col_label_bot = Text("Test Negative (-)", font_size=24).next_to(box, DOWN, buff=0.3)
        row_label_sick = Text("Sick", font_size=24).next_to(box, LEFT, buff=0.3).shift(UP * box_height/4)
        row_label_healthy = Text("Healthy", font_size=24).next_to(box, LEFT, buff=0.3).shift(DOWN * box_height/4)

        # Title
        title = Text("Bayes' Theorem: The Medical Test Paradox", font_size=32)
        title.to_edge(UP)

        # Initial Population Text
        pop_text = Text(f"Total Population: {total_population}", font_size=24)
        pop_text.next_to(box, DOWN, buff=0.8)

        # --- Animation Sequence ---
        
        # 1. Setup
        self.play(Write(title))
        self.play(Create(box), Create(h_line), Create(v_line))
        self.play(
            Write(col_label_top), Write(col_label_bot),
            Write(row_label_sick), Write(row_label_healthy)
        )
        self.play(Write(pop_text))
        self.wait(1)

        # 2. Populate Counts (Fade in rectangles and numbers)
        self.play(
            FadeIn(tl_rect), FadeIn(tr_rect), FadeIn(bl_rect), FadeIn(br_rect),
            FadeIn(tl_label), FadeIn(tr_label), FadeIn(bl_label), FadeIn(br_label),
            run_time=2
        )
        self.wait(1)

        # 3. Highlight the "Test Positive" Row (Top Half)
        # We want to calculate P(Sick | +), so we focus on the top row
        top_row_group = VGroup(tl_rect, tr_rect, tl_label, tr_label, h_line)
        
        highlight_box = SurroundingRectangle(
            VGroup(tl_rect, tr_rect), 
            color=YELLOW, buff=0.05, stroke_width=3
        )
        
        explanation_text = Text(
            "We know the test is Positive.\nFocus only on the top row.", 
            font_size=24, color=YELLOW
        ).next_to(highlight_box, RIGHT, buff=0.5)

        self.play(
            Create(highlight_box),
            Write(explanation_text),
            tl_label.animate.set_color(YELLOW),
            tr_label.animate.set_color(YELLOW),
            run_time=2
        )
        self.wait(2)

        # 4. Show the Calculation Formula
        # P(Sick | +) = TP / (TP + FP)
        
        formula_num = MathTex(r"\text{Sick} \cap +", "=", str(tp)).scale(0.8)
        formula_denom = MathTex(r"(\text{Sick} \cap +) + (\text{Not Sick} \cap +)", "=", f"{tp} + {fp}", "=", str(tp+fp)).scale(0.8)
        
        formula_num.next_to(highlight_box, DOWN, buff=1.5).align_to(highlight_box, LEFT)
        formula_denom.next_to(formula_num, DOWN, buff=0.5).align_to(formula_num, LEFT)
        
        fraction_line = Line(
            start=formula_num.get_bottom() + DOWN*0.1,
            end=formula_denom.get_top() + UP*0.1
        )
        # Adjust alignment for fraction look
        formula_denom.shift(LEFT * (formula_denom.get_width() - formula_num.get_width())/2)
        fraction_line.match_x(formula_num)
        
        equals_sign = MathTex("=").scale(1.5).next_to(fraction_line, RIGHT, buff=0.2)
        
        # Calculate result
        prob_val = tp / (tp + fp)
        result_text = MathTex(f"{prob_val:.4f}", color=GOLD).scale(1.2).next_to(equals_sign, RIGHT, buff=0.2)
        
        final_label = Text("P(Sick | +) =", font_size=28).next_to(formula_num, LEFT, buff=0.2)

        self.play(
            Write(final_label),
            Write(formula_num),
            Write(formula_denom),
            Create(fraction_line),
            Write(equals_sign),
            run_time=2
        )
        self.wait(1)
        self.play(Write(result_text))
        self.wait(1)

        # 5. The Paradox Explanation
        paradox_title = Text("The Paradox", font_size=32, color=RED).to_edge(DOWN, buff=1.5)
        paradox_point1 = Text(
            "Test Accuracy: 95%", 
            font_size=24
        ).next_to(paradox_title, DOWN, aligned_edge=LEFT)
        paradox_point2 = Text(
            "Prevalence: 0.1% (1 in 1000)", 
            font_size=24
        ).next_to(paradox_point1, DOWN, aligned_edge=LEFT)
        paradox_point3 = Text(
            f"Result: Only {prob_val*100:.1f}% chance you are actually sick!", 
            font_size=24, color=GOLD
        ).next_to(paradox_point2, DOWN, aligned_edge=LEFT)
        
        reason_text = Text(
            "False Positives (Healthy people) vastly outnumber\nTrue Positives (Sick people) due to low prevalence.",
            font_size=20, color=LIGHT_GRAY
        ).next_to(paradox_point3, DOWN, buff=0.5)

        self.play(
            FadeOut(explanation_text),
            FadeOut(highlight_box),
            Write(paradox_title),
            Write(paradox_point1),
            Write(paradox_point2),
            Write(paradox_point3),
            Write(reason_text),
            run_time=3
        )
        
        # Final highlight on the False Positives vs True Positives visual comparison
        self.play(
            tr_rect.animate.set_fill(color=BLUE, opacity=0.8), # Emphasize False Positives
            tl_rect.animate.set_fill(color=RED, opacity=0.8),  # Emphasize True Positives
            run_time=1
        )
        
        self.wait(3)
from manim import *

class BayesBox(Scene):
    def construct(self):
        # Title
        title = Text("Bayes' Theorem: The Medical Test Paradox", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        
        # Create the main rectangle (Bayes box)
        box = Rectangle(width=6, height=4, color=WHITE)
        box.move_to(ORIGIN)
        
        # Create dividing lines
        vertical_line = Line(box.get_top(), box.get_bottom(), color=WHITE)
        horizontal_line = Line(box.get_left(), box.get_right(), color=WHITE)
        
        # Draw the box and lines
        self.play(Create(box))
        self.play(Create(vertical_line), Create(horizontal_line))
        
        # Labels for the quadrants
        sick_pos = Text("Sick & +", font_size=20, color=RED)
        sick_pos.move_to(box.get_corner(UL) + [1.5, -0.5, 0])
        
        healthy_pos = Text("Healthy & +", font_size=20, color=ORANGE)
        healthy_pos.move_to(box.get_corner(UR) + [-1.5, -0.5, 0])
        
        sick_neg = Text("Sick & -", font_size=20, color=PINK)
        sick_neg.move_to(box.get_corner(DL) + [1.5, 0.5, 0])
        
        healthy_neg = Text("Healthy & -", font_size=20, color=GREEN)
        healthy_neg.move_to(box.get_corner(DR) + [-1.5, 0.5, 0])
        
        # Add labels
        self.play(
            Write(sick_pos),
            Write(healthy_pos),
            Write(sick_neg),
            Write(healthy_neg)
        )
        self.wait(1)
        
        # Initial setup text
        setup_text = VGroup(
            Text("Setup:", font_size=24, color=YELLOW),
            Text("• Population: 1000 people", font_size=20),
            Text("• Disease prevalence: 0.1% (1 in 1000)", font_size=20),
            Text("• Test accuracy: 95%", font_size=20),
            Text("  - Sensitivity: 95% (detects 95% of sick)", font_size=18),
            Text("  - Specificity: 95% (correctly identifies 95% of healthy)", font_size=18)
        ).arrange(DOWN, aligned_edge=LEFT)
        setup_text.to_edge(LEFT, buff=0.5)
        
        self.play(Write(setup_text))
        self.wait(2)
        
        # Step 1: Show initial population
        step1_text = Text("Step 1: Initial Population", font_size=24, color=YELLOW)
        step1_text.move_to(setup_text[0].get_center())
        
        self.play(Transform(setup_text[0], step1_text))
        self.play(FadeOut(setup_text[1:]))
        
        # Add numbers to quadrants
        # 1 sick person out of 1000
        sick_total = 1
        healthy_total = 999
        
        # Test results (95% accuracy)
        sick_pos_count = int(sick_total * 0.95)  # 1 * 0.95 ≈ 1
        sick_neg_count = sick_total - sick_pos_count  # 0
        
        healthy_pos_count = int(healthy_total * 0.05)  # 999 * 0.05 ≈ 50
        healthy_neg_count = healthy_total - healthy_pos_count  # 949
        
        # Numbers for each quadrant
        num_sick_pos = Text(f"{sick_pos_count}", font_size=32, color=RED, weight=BOLD)
        num_sick_pos.move_to(box.get_corner(UL) + [1.5, -1.2, 0])
        
        num_healthy_pos = Text(f"{healthy_pos_count}", font_size=32, color=ORANGE, weight=BOLD)
        num_healthy_pos.move_to(box.get_corner(UR) + [-1.5, -1.2, 0])
        
        num_sick_neg = Text(f"{sick_neg_count}", font_size=32, color=PINK, weight=BOLD)
        num_sick_neg.move_to(box.get_corner(DL) + [1.5, 1.2, 0])
        
        num_healthy_neg = Text(f"{healthy_neg_count}", font_size=32, color=GREEN, weight=BOLD)
        num_healthy_neg.move_to(box.get_corner(DR) + [-1.5, 1.2, 0])
        
        self.play(
            Write(num_sick_pos),
            Write(num_healthy_pos),
            Write(num_sick_neg),
            Write(num_healthy_neg)
        )
        self.wait(2)
        
        # Step 2: Highlight positive tests
        step2_text = Text("Step 2: Focus on Positive Tests", font_size=24, color=YELLOW)
        self.play(Transform(setup_text[0], step2_text))
        
        # Create highlight rectangles for positive tests
        pos_highlight_left = Rectangle(
            width=3, height=2, color=YELLOW, fill_opacity=0.3
        ).move_to(box.get_corner(UL) + [1.5, -1, 0])
        
        pos_highlight_right = Rectangle(
            width=3, height=2, color=YELLOW, fill_opacity=0.3
        ).move_to(box.get_corner(UR) + [-1.5, -1, 0])
        
        self.play(
            Create(pos_highlight_left),
            Create(pos_highlight_right)
        )
        self.wait(1)
        
        # Step 3: Calculate Bayes' theorem
        step3_text = Text("Step 3: Calculate P(Sick | Positive Test)", font_size=24, color=YELLOW)
        self.play(Transform(setup_text[0], step3_text))
        
        # Calculation
        total_positive = sick_pos_count + healthy_pos_count
        probability = sick_pos_count / total_positive if total_positive > 0 else 0
        
        calc_text = VGroup(
            Text("P(Sick | +) = ", font_size=20),
            Text("Sick & Positive", font_size=20, color=RED),
            Text("─────────────────", font_size=20),
            Text("Total Positive", font_size=20, color=YELLOW),
            Text(f"= {sick_pos_count} / {total_positive} = {probability:.1%}", font_size=20, color=BLUE, weight=BOLD)
        ).arrange(DOWN)
        calc_text.to_edge(RIGHT, buff=0.5)
        
        self.play(Write(calc_text))
        self.wait(2)
        
        # Highlight the paradox
        paradox_box = Rectangle(width=4, height=1.5, color=RED, stroke_width=3)
        paradox_box.surround(calc_text[-1], buff=0.2)
        
        self.play(Create(paradox_box))
        self.wait(1)
        
        # Final explanation
        explanation = VGroup(
            Text("The Paradox:", font_size=24, color=RED, weight=BOLD),
            Text("• Test is 95% accurate", font_size=18),
            Text("• But only 2% chance of being sick if positive!", font_size=18, color=RED),
            Text("• Why? Very low disease prevalence (0.1%)", font_size=18),
            Text("• Most positive tests are false positives", font_size=18, color=ORANGE)
        ).arrange(DOWN, aligned_edge=LEFT)
        explanation.to_edge(DOWN, buff=0.5)
        
        self.play(Write(explanation))
        self.wait(3)
        
        # Fade out everything
        self.play(
            *[FadeOut(mob) for mob in self.mobjects]
        )
        self.wait(1)
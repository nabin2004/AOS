from manim import *

class BayesTheoremVisualization(Scene):
    def construct(self):
        # Title
        title = Text("Bayes' Theorem Visualization", font_size=36)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        # Create grid of rectangles
        grid = VGroup()
        for i in range(2):
            for j in range(2):
                rect = Rectangle(
                    width=2,
                    height=2,
                    fill_opacity=0.8,
                    stroke_width=2
                )
                if i == 0 and j == 0:
                    rect.set_fill(BLUE, opacity=0.8)
                    label = Text("P(sick ∩ +)", font_size=24).move_to(rect.get_center())
                elif i == 0 and j == 1:
                    rect.set_fill(GREEN, opacity=0.8)
                    label = Text("P(not-sick ∩ +)", font_size=24).move_to(rect.get_center())
                elif i == 1 and j == 0:
                    rect.set_fill(RED, opacity=0.8)
                    label = Text("P(sick ∩ −)", font_size=24).move_to(rect.get_center())
                else:
                    rect.set_fill(YELLOW, opacity=0.8)
                    label = Text("P(not-sick ∩ −)", font_size=24).move_to(rect.get_center())
                
                group = VGroup(rect, label)
                grid.add(group)
        
        grid.arrange_in_grid(rows=2, cols=2, buff=0.5)
        grid.move_to(ORIGIN)
        
        self.play(Create(grid))
        self.wait(1)

        # Initial counts
        initial_counts = [
            "Sick +: 1",
            "Not Sick +: 99",
            "Sick -: 99",
            "Not Sick -: 990"
        ]
        
        for i, count_text in enumerate(initial_counts):
            count = Text(count_text, font_size=20).next_to(grid[i], DOWN, buff=0.2)
            self.play(Write(count))
        
        self.wait(1)

        # Highlight sick population who tested +
        sick_positive_rect = grid[0]
        sick_positive_label = Text("Sick Population\nWho Tested Positive", font_size=20, color=WHITE).move_to(sick_positive_rect.get_center())
        self.play(
            TransformFromCopy(sick_positive_rect, sick_positive_label),
            sick_positive_rect.animate.set_fill(BLUE, opacity=0.5)
        )
        self.wait(1)

        # Final calculation
        calc_text = MathTex(r"P(\text{sick} \mid \text{+}) = \frac{\text{Top-Left}}{\text{Top-Left} + \text{Top-Right}}")
        calc_text.to_edge(UP)
        self.play(Write(calc_text))
        self.wait(1)

        # Final probability
        final_prob = DecimalNumber(0.01, font_size=36).to_edge(DOWN)
        prob_text = Text("Final Probability:", font_size=24).next_to(final_prob, UP)
        explanation = Text("Paradox: Test is 95% accurate,\nbut low disease prevalence →\nhigh false positive rate", font_size=20).to_edge(RIGHT)
        
        self.play(
            Write(prob_text),
            Write(final_prob),
            Write(explanation)
        )
        self.wait(2)

        # Clear scene
        self.play(
            FadeOut(grid),
            FadeOut(initial_counts),
            FadeOut(sick_positive_label),
            FadeOut(calc_text),
            FadeOut(final_prob),
            FadeOut(prob_text),
            FadeOut(explanation)
        )
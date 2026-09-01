from manim import *

class BayesTheoremVisualization(Scene):
    def construct(self):
        # Title
        title = Text("Bayes' Theorem Visualization", font_size=36)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        # Create grid
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
                    label = Text("P(sick ∩ -)", font_size=24).move_to(rect.get_center())
                else:
                    rect.set_fill(YELLOW, opacity=0.8)
                    label = Text("P(not-sick ∩ -)", font_size=24).move_to(rect.get_center())
                
                group = VGroup(rect, label)
                group.move_to([i*3, -j*3, 0])
                grid.add(group)
        
        self.play(Create(grid))
        self.wait(1)

        # Add initial counts
        count_text = VGroup()
        for i, g in enumerate(grid):
            count = MathTex(f"{i+1}", font_size=36).next_to(g[0], DOWN)
            count_text.add(count)
        
        self.play(Write(count_text))
        self.wait(1)

        # Highlight sick positives
        sick_positives = grid[0][0]
        self.play(
            sick_positives.animate.set_fill(BLUE, opacity=1),
            run_time=1.5
        )

        # Calculate conditional probability
        prob_text = MathTex(r"P(\text{sick} \mid +) = \frac{P(\text{sick} \cap +)}{P(\text{sick} \cap +) + P(\text{not-sick} \cap +)}", font_size=36)
        prob_text.to_edge(UP)
        self.play(Write(prob_text))
        self.wait(1)

        # Final probability value
        final_prob = MathTex(r"\approx 0.05", font_size=36)
        final_prob.next_to(prob_text, DOWN)
        self.play(Write(final_prob))
        self.wait(1)

        # Explanation
        explanation = Text("Paradox: Test is 95% accurate, but low disease prevalence\nleads to high false positive rate.", font_size=24)
        explanation.to_edge(DOWN)
        self.play(Write(explanation))
        self.wait(2)

        # Fade out everything
        self.play(*[FadeOut(mob) for mob in self.mobjects])
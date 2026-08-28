from manim import *


class BODMASScene(Scene):
    def construct(self):
        title = Text("Understanding BODMAS", font_size=48)
        self.play(Write(title))
        self.wait(1)

        rules = Text("BODMAS stands for:", font_size=36)
        self.play(Write(rules))
        self.wait(1)

        bodmas_parts = ["B: Brackets", "O: Orders", "D: Division", "M: Multiplication", "A: Addition", "S: Subtraction"]
        bodmas_text = VGroup(*[Text(part, font_size=24) for part in bodmas_parts])
        bodmas_text.arrange(DOWN, buff=0.5)

        self.play(FadeIn(bodmas_text))
        self.wait(2)

        example_expression = Text("Example: 3 + 2 \times (4 - 1)", font_size=32)
        self.play(Write(example_expression))
        self.wait(1)

        self.play(FadeOut(title), FadeOut(rules), FadeOut(bodmas_text))
        self.play(Write(example_expression))
        self.wait(2)

        explanation = Text("Step 1: Solve Brackets: (4 - 1) = 3", font_size=24)
        self.play(Write(explanation))
        self.wait(1)

        final_expression = Text("3 + 2 \times 3", font_size=32)
        self.play(Transform(example_expression, final_expression))
        self.wait(1)

        explanation2 = Text("Step 2: Multiplication: 2 \times 3 = 6", font_size=24)
        self.play(Write(explanation2))
        self.wait(1)

        final_result = Text("3 + 6 = 9", font_size=32)
        self.play(Transform(example_expression, final_result))
        self.wait(2)

        end_text = Text("Final Answer: 9", font_size=36)
        self.play(Write(end_text))
        self.wait(2)

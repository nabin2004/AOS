from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService
import numpy as np

class AOSTrajectoryScene118(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba",cache_dir="voiceover_cache"))

        title = Title("Can you write a manim code for teachi")
        ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 5, 1], x_length=6, y_length=4)
        curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=BLUE)
        label = MathTex(r'\sigma(x) = \frac{1}{1 +e^{-x}}').to_corner(UR)
        dot = Dot(ax.c2p(0, 0.5), color=RED)

        with self.voiceover(
            text="Let's visualize the sigmoid function. <bookmarkmark='show_axes'/> Here is our coordinate system. <bookmarkmark='show_curve'/> We plot the curve defined by the function sigma of xequals one over one plus e to the negative x. <bookmark mark='move_dot'/> And we can track a point as it moves along the curve."
        ) as tracker:
            self.play(Write(title))
            self.wait_until_bookmark("show_axes")
            self.play(Create(ax), Write(label))
            self.wait_until_bookmark("show_curve")
            self.play(Create(curve), FadeIn(dot))
            self.wait_until_bookmark("move_dot")
            self.play(dot.animate.move_to(ax.c2p(2, 1 / (1 + np.exp(-2)))), run_time=2)

        self.wait(1)

from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class BodmasScene(VoiceoverScene):
    def construct(self):
        # Configure voice service
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))

        title = Title("The BODMAS Rule")

        # 1. BODMAS Ladder on the Left
        ladder_items = [
            ("B", "Brackets", r"(5 - 3)"),
            ("O", "Orders (Powers)", r"2^2"),
            ("D", "Division", r"\div 4"),
            ("M", "Multiplication", r"\times 4"),
            ("A", "Addition", r"8 + 4"),
            ("S", "Subtraction", r"-"),
        ]
        ladder_group = VGroup()
        for letter, full, _ in ladder_items:
            t = Text(f"{letter} - {full}", font_size=28)
            ladder_group.add(t)
        ladder_group.arrange(DOWN, aligned_edge=LEFT, buff=0.35).to_edge(LEFT, buff=0.8)

        # 2. Equation Steps
        eq1 = MathTex(r"8 + 2 \times (5 - 3)^2 \div 4", font_size=42).shift(RIGHT * 2 + UP * 1.5)
        eq2 = MathTex(r"8 + 2 \times 2^2 \div 4", font_size=42).move_to(eq1)
        eq3 = MathTex(r"8 + 2 \times 4 \div 4", font_size=42).move_to(eq1)
        eq4 = MathTex(r"8 + 8 \div 4", font_size=42).move_to(eq1)
        eq5 = MathTex(r"8 + 2", font_size=42).move_to(eq1)
        eq6 = MathTex(r"= 10", font_size=52, color=YELLOW).next_to(eq5, DOWN, buff=0.8)

        with self.voiceover(
            text="Welcome! Today we will learn the BODMAS rule for order of operations. <bookmark mark='SHOW_LADDER'/> BODMAS stands for Brackets, Orders, Division, Multiplication, Addition, and Subtraction. <bookmark mark='SHOW_EQ'/> Let's solve this expression together."
        ) as tracker:
            self.play(Write(title))
            self.wait_until_bookmark("SHOW_LADDER")
            self.play(FadeIn(ladder_group, shift=RIGHT))
            self.wait_until_bookmark("SHOW_EQ")
            self.play(Write(eq1), run_time=tracker.duration)

        # Step B: Brackets
        with self.voiceover(
            text="First, we evaluate the Brackets. Five minus three equals two."
        ) as tracker:
            self.play(ladder_group[0].animate.set_color(YELLOW))
            box = SurroundingRectangle(eq1[0][6:11], color=YELLOW)
            self.play(Create(box))
            self.play(ReplacementTransform(eq1, eq2), FadeOut(box), run_time=tracker.duration)
            self.play(ladder_group[0].animate.set_color(WHITE))

        # Step O: Orders
        with self.voiceover(
            text="Next are Orders, or powers. Two squared equals four."
        ) as tracker:
            self.play(ladder_group[1].animate.set_color(YELLOW))
            box = SurroundingRectangle(eq2[0][6:8], color=YELLOW)
            self.play(Create(box))
            self.play(ReplacementTransform(eq2, eq3), FadeOut(box), run_time=tracker.duration)
            self.play(ladder_group[1].animate.set_color(WHITE))

        # Step M & D: Multiplication and Division (Left to Right)
        with self.voiceover(
            text="Now we handle Multiplication and Division from left to right. Two times four is eight, and eight divided by four is two."
        ) as tracker:
            self.play(ladder_group[3].animate.set_color(YELLOW))
            box = SurroundingRectangle(eq3[0][2:5], color=YELLOW)
            self.play(Create(box))
            self.play(ReplacementTransform(eq3, eq4), FadeOut(box))
            self.play(ladder_group[3].animate.set_color(WHITE), ladder_group[2].animate.set_color(YELLOW))
            box2 = SurroundingRectangle(eq4[0][2:5], color=YELLOW)
            self.play(Create(box2))
            self.play(ReplacementTransform(eq4, eq5), FadeOut(box2), run_time=tracker.duration)
            self.play(ladder_group[2].animate.set_color(WHITE))

        # Step A: Addition
        with self.voiceover(
            text="Finally, we perform Addition. Eight plus two gives our final answer, ten."
        ) as tracker:
            self.play(ladder_group[4].animate.set_color(YELLOW))
            self.play(Write(eq6), run_time=tracker.duration)
            self.play(ladder_group[4].animate.set_color(WHITE))

        self.wait(1)


from manim import *
import numpy as np

class PedagogicalScene161(Scene):
    def construct(self):
        title = Title("What is 2 + 3 × 4?")
        self.play(Write(title))
        self.wait(1)

        eq1 = MathTex(r"(2 + 3) \times 4 = 20").to_edge(UP)
        eq2 = MathTex(r"2 + (3 \times 4) = 14").next_to(eq1, DOWN, buff=0.6)
        self.play(Write(eq1))
        self.wait(1)
        self.play(Write(eq2))
        self.wait(2)

        correct_answer = MathTex(r"\text{Correct answer: } 14").next_to(eq2, DOWN, buff=0.4)
        self.play(FadeIn(correct_answer))
        self.wait(1)

        self.play(
            eq1.animate.set_color(GOLD),
            eq2.animate.set_color(GOLD),
            correct_answer.animate.set_color(GREEN),
            run_time=1.5
        )
        self.wait(2)
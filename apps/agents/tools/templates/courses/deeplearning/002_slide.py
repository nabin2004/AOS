from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService


class Slides2(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="alba", 
                             cache_dir="voiceover_cache",         
                             generate_subtitles=True,
        ))

        with self.voiceover(text="Hellooo, Nabin. How are you? And I just so excited to have you here. First of all, Welcome to CS231n.   I'm your instructor for this course, and I'll be guiding you through this journey. We majorly will be focusing on deep learning techniques for computer vision including some of the latest advancements as well.") as tracker:
            title = Text(
                "CS231n: Deep Learning for Computer Vision",
                font="Arial",
                weight=BOLD,
                color=BLUE,
            )
            
            subtitle = Text(
                "Lecture 1: Introduction",
                font="Arial",
                weight=BOLD,
                color=GREEN,
            )

            # --- FIX 1: AUTO-ADJUST WIDTH ---
            # Scale each text block to fit 90% of the frame's width
            max_width = config.frame_width * 0.9
            
            # Method 1: Using scale_to_fit_width (most direct)
            title.scale_to_fit_width(max_width)
            subtitle.scale_to_fit_width(max_width * 0.6)  # Subtitle narrower
            
            # --- FIX 2: PREVENT OVERLAPPING ---
            # Group them and arrange vertically with a buffer
            text_group = VGroup(title, subtitle).arrange(DOWN, buff=0.5)
            text_group.move_to(ORIGIN)  # Center the entire group

            # Animate them
            self.play(Write(title, run_time=min(tracker.duration * 0.7, 2.0)))
            self.play(Write(subtitle, run_time=min(tracker.duration * 0.7, 2.0)))

        self.wait(1)


class Slides4(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="jane",
                             cache_dir="voiceover_cache",
                             generate_subtitles=True,
        ))

        with self.voiceover(text="So here is our <bookmark mark='FOCUS'/>lecture One Introduction."):
            title = Title("Lecture 1: Introduction", font_size=48, color=BLUE)
            self.wait_until_bookmark("FOCUS")
            self.play(Write(title))

        self.wait(1)

        with self.voiceover(text="In this lecture, we will cover the following topics: <bookmark mark='TOPICS'/>1. What is Deep Learning? 2. Why Deep Learning for Computer Vision? 3. Overview of the Course Structure and Content."):
            topics = BulletedList(
                "What is Deep Learning?",
                "Why Deep Learning for Computer Vision?",
                "Overview of the Course Structure and Content.",
                font_size=36,
                color=WHITE
            )
            self.wait_until_bookmark("TOPICS")
            self.play(Write(topics))

        self.wait(1)

class Slides5(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="jane",
                             cache_dir="voiceover_cache",
                             generate_subtitles=True,
        ))

        with self.voiceover(text="Let's walk through the code below. Generally, we use python language most of the time for deep learning. And most code in deep learning is easy to write if we understand the concepts.") as tracker:
            title = Title("CodeWalkthrough", font_size=48, color=BLUE)
            self.play(Write(title), run_time=min(tracker.duration * 0.7, 2.0))

        self.wait(1)

        with self.voiceover(
            text=(
                "So let's start with the first line of code. "
                "We import the necessary libraries and modules required. "
                "Let's first import numpy "
                "<bookmark mark='NUMPY'/>"
                "and then import the torch library."
                "<bookmark mark='TORCH'/>"
            )
        ) as tracker:

            # Create the complete code block once
            code = Code(
                code_string="""\
import numpy as np
import torch
""",
                tab_width=4,
                background="window",
                language="python",
            )

            # Don't display it yet
            code.set_opacity(0)

            self.add(code)

            # NUMPY bookmark
            self.wait_until_bookmark("NUMPY")

            # Reveal the first line
            # Adjust these indices depending on your Manim version.
            numpy_line = code[2][0]
            numpy_line.set_opacity(1)

            self.play(
                FadeIn(numpy_line),
                run_time=0.5
            )

            # TORCH bookmark
            self.wait_until_bookmark("TORCH")

            torch_line = code[2][1]
            torch_line.set_opacity(1)

            self.play(
                FadeIn(torch_line),
                run_time=0.5
            )

        self.wait(1)


class Slides6(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(
                voice="jane",
                cache_dir="voiceover_cache",
                generate_subtitles=True,
            )
        )

        with self.voiceover(
            text=(
                "Now let me show you Euler's formula. "
                "See carefully, "
                "<bookmark mark='EXP'/>e to the power of i x"
                "<bookmark mark='EQUALS'/>is equal to  "
                "<bookmark mark='COS'/>cos x"
                "<bookmark mark='PLUS'/>plus"
                "<bookmark mark='SIN'/>i sine x"
            )
        ) as tracker:

            eqn = MathTex(
                r"e^{ix}",
                r"=",
                r"\cos x",
                r"+",
                r"i\sin x",
            )

            eqn.arrange(RIGHT)

            # Show the complete equation immediately
            self.play(Write(eqn), run_time=0.5)

            # "e to the power of i x"
            self.wait_until_bookmark("EXP")
            self.play(
                Indicate(eqn[0]),
                run_time=0.5
            )

            # "is equal to"
            self.wait_until_bookmark("EQUALS")
            self.play(
                Indicate(eqn[1]),
                run_time=0.5
            )

            # "cos x"
            self.wait_until_bookmark("COS")
            self.play(
                Indicate(eqn[2]),
                run_time=0.5
            )

            # "plus"
            self.wait_until_bookmark("PLUS")
            self.play(
                Indicate(eqn[3]),
                run_time=0.5
            )

            # "i sine x"
            self.wait_until_bookmark("SIN")
            self.play(
                Indicate(eqn[4]),
                run_time=0.5
            )

        self.wait(1)
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService


class Slides(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )
        def create_intro_slide(title_text, subtitle_text, voiceover_text):
            pass 

        def create_content_slide(title_text, voiceover_text):
            pass 

        def create_conclusion_slide(title_text, voiceover_text):
            pass 

        def create_footer(footer_text):
            pass 

        def create_slide(title_text, subtitle_text=None):
            pass 

        def create_visualize_concept(concept_text, voiceover_text):
            pass


        # ## Slide 1: Introduction
        # with self.voiceover(text="Welcome to CS231n, Deep Learning for Computer Vision. I'm your instructor, and I'll be guiding you through this journey.") as tracker:
        #     # Main title with elegant styling
        #     title = Text(
        #         "CS231n: Deep Learning for Computer Vision",
        #         font="Arial",
        #         weight=BOLD,
        #         color=BLUE,
        #         # font_size=60
        #     )
            
        #     # Subtitle with subtle styling
        #     subtitle = Text(
        #         "Lecture 1: Introduction",
        #         font="Arial",
        #         color=WHITE,
        #         # font_size=36,
        #         opacity=0.8
        #     ).next_to(title, DOWN, buff=0.5)
            
        #     # Create a VGroup for smooth animation
        #     title_group = VGroup(title, subtitle)
            
        #     # Animate title with a graceful write-in
        #     self.play(Write(title, run_time=min(tracker.duration * 0.7, 2.0)))
            
        #     # Subtitle fades in with a slight delay
        #     self.play(
        #         FadeIn(subtitle, shift=UP * 0.2),
        #         run_time=min(tracker.duration * 0.3, 0.8)
        #     )
            
        #     # Hold the complete frame for remaining time
        #     if tracker.duration > 2.8:
        #         self.wait(tracker.duration - 2.8)
        #         self.wait(1)

        # ## Slide 2: Overview of Deep Learning
        # with self.voiceover(text="In this lecture, we'll explore the foundations of deep learning—starting with neural networks, then backpropagation, and finally convolutional neural networks. Let's get started!") as tracker:
        #     # Main title with accent line for visual interest
        #     overview_title = Text(
        #         "Overview of Deep Learning",
        #         font="Arial",
        #         weight=BOLD,
        #         color=BLUE,
        #         font_size=54
        #     )
            
        #     # Decorative underline
        #     title_underline = Line(
        #         start=LEFT, 
        #         end=RIGHT, 
        #         color=BLUE_D, 
        #         stroke_width=3
        #     ).scale(0.8).next_to(overview_title, DOWN, buff=0.1)
            
        #     # Course topics with numbered hierarchy and icons
        #     topic_1 = Text("1. Neural Networks", font="Arial", color=WHITE, font_size=40)
        #     topic_2 = Text("2. Backpropagation", font="Arial", color=WHITE, font_size=40)
        #     topic_3 = Text("3. Convolutional Neural Networks", font="Arial", color=WHITE, font_size=40)
            
        #     # Add subtle bullet points
        #     for topic in [topic_1, topic_2, topic_3]:
        #         bullet = Text("▸", color=BLUE_C, font_size=40).next_to(topic, LEFT, buff=0.3)
        #         topic.become(VGroup(bullet, topic))
            
        #     overview_points = VGroup(topic_1, topic_2, topic_3).arrange(
        #         DOWN, 
        #         aligned_edge=LEFT, 
        #         buff=0.6
        #     ).next_to(title_underline, DOWN, buff=0.6)
            
        #     # Animate with staggered timing for elegance
        #     self.play(
        #         Write(overview_title, run_time=min(tracker.duration * 0.3, 1.2)),
        #         GrowFromCenter(title_underline, run_time=min(tracker.duration * 0.2, 0.6))
        #     )
            
        #     # Stagger bullet points for dramatic effect
        #     for i, point in enumerate(overview_points):
        #         self.play(
        #             FadeIn(point, shift=RIGHT * 0.3),
        #             run_time=min(tracker.duration * 0.15, 0.5)
        #         )
        #         if i < len(overview_points) - 1:  # Small pause between items
        #             self.wait(0.1)
            
        #     # Hold with a smooth pulse effect if time allows
        #     remaining_time = tracker.duration - (min(tracker.duration * 0.3, 1.2) + 
        #                                         len(overview_points) * min(tracker.duration * 0.15, 0.5) + 
        #                                         0.2)
        #     if remaining_time > 0.5:
        #         self.wait(remaining_time - 0.3)
        #         # Subtle emphasis on the last point
        #         self.play(
        #             overview_points[-1].animate.scale(1.02).set_color(YELLOW),
        #             run_time=0.3,
        #             rate_func=rate_functions.there_and_back
        #         )
        #     elif remaining_time > 0:
        #         self.wait(remaining_time)

        
from __future__ import annotations

from manim import (
    BLUE,
    DOWN,
    LEFT,
    MED_SMALL_BUFF,
    RIGHT,
    UP,
    WHITE,
    FadeIn,
    FadeOut,
    Line,
    SurroundingRectangle,
    Text,
    Title,
    Transform,
    Unwrite,
    VGroup,
    Write,
)
from aos_manim_slides import MarkdownVoiceoverDeck, Slide, VoiceoverSlideScene


class BrandedBackpropDeck(VoiceoverSlideScene):
    """Full educational video with branded intro, opening music, and synchronized lecture slides."""

    markdown_file: str = "backprop_presentation.md"
    voice: str = "alba"
    voiceover_cache: str = "voiceover_cache"
    opening_sound: str = "audio/brand_intro.mp3"


    def construct(self):
        # 1. Enable resident voiceover service
        self.enable_voiceover(voice=self.voice, cache_dir=self.voiceover_cache)

        # 2. Opening Branding Intro with Audio
        self.play_branding_intro()

        # 3. Present Slides with Voiceover and Progressive Revelation
        with open(self.markdown_file, "r", encoding="utf-8") as f:
            md_content = f.read()

        for slide in Slide.deck_from_markdown(md_content):
            self.show_slide(slide, transition="fade", lecture=True)
            self.pause_slide(self.lecture_gap)

    def play_branding_intro(self):
        # Trigger opening brand music
        try:
            self.add_sound(self.opening_sound)
        except Exception:
            pass

        brand = Text("RUKUMINI", font_size=70, color=BLUE)
        self.play(Write(brand), run_time=1.2)
        self.wait(0.5)

        box = SurroundingRectangle(brand, color=WHITE, buff=MED_SMALL_BUFF)
        nabin = Text("by Nabin", font_size=30, color=WHITE).move_to(DOWN * 0.9)
        self.play(Write(box), FadeIn(nabin, shift=UP * 0.2), run_time=0.9)
        self.wait(1.2)

        # Transition into lecture topic
        title = Text("Lecture 1", font_size=42, color=WHITE).to_edge(UP, buff=1.0)
        topic = Text("Backpropagation", font_size=54, color=BLUE)
        subtitle = Text("Teaching a Neural Network to Learn", font_size=28, color=WHITE).move_to(DOWN * 0.9)

        self.play(
            FadeOut(brand),
            FadeOut(box),
            FadeOut(nabin),
            FadeIn(title, shift=DOWN * 0.2),
            FadeIn(topic, shift=UP * 0.2),
            FadeIn(subtitle, shift=UP * 0.2),
            run_time=1.2,
        )
        self.wait(1.8)

        # Clear branding intro smoothly before first slide enters
        self.play(FadeOut(VGroup(title, topic, subtitle)), run_time=0.8)
        self.wait(0.3)

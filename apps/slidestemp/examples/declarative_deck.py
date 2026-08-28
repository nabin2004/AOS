from __future__ import annotations

from pathlib import Path

from aos_manim_core import set_theme
from aos_manim_slides import Slide, VoiceoverSlideScene


DECK_PATH = Path(__file__).parent / "slides" / "calculus_methods.md"


class DeclarativeMethodsScene(VoiceoverSlideScene):
    """Markdown deck with lecture cues: gradual reveal, then diagram steps."""

    def construct(self):
        set_theme("academic_oxford")
        markdown = DECK_PATH.read_text(encoding="utf-8")
        for slide in Slide.deck_from_markdown(markdown):
            self.show_slide(slide, transition="fade", lecture=True)
            self.pause_slide(0.4)

"""London-style bookmark loop: wait, then reveal / highlight content.

Render:
  manim -ql examples/lecture_cues.py LectureCuesScene
"""

from __future__ import annotations

from aos_manim_core import set_theme
from aos_manim_slides import Slide, VoiceoverSlideScene
from aos_manim_slides.document.model import ListBlock, SlideSpec


class LectureCuesScene(VoiceoverSlideScene):
    """Hand-authored voiceover bookmarks mapped onto list items."""

    def construct(self):
        set_theme("academic_oxford")
        slide = Slide.from_spec(
            SlideSpec(
                title="Lecture cues",
                layout="title-content",
                blocks=[
                    ListBlock(
                        items=[
                            "Reveal the next idea as it is spoken",
                            "Highlight the active fragment",
                            "Step a diagram or algorithm in time with the voice",
                        ]
                    )
                ],
                voiceover=(
                    "Three moves, the same pattern as a voiceover lecture. "
                    "<bookmark mark='li0'/>Reveal. "
                    "<bookmark mark='li1'/>Highlight. "
                    "<bookmark mark='li2'/>Step."
                ),
            )
        )
        self.show_slide(slide, lecture=True)
        self.pause_slide(0.5)

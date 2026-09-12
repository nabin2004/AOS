"""Consumer module for EduClaw asynchronous streaming pipeline.

Renders discrete, sequential chunked MP4 video files per slide using Manim Community Edition
and VoiceoverScene, enabling true low-latency slide-by-slide streaming to web frontends.
"""

from __future__ import annotations

import os
import queue
import sys
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

from apps.educlaw.streaming_engine.models import SlideData


def get_speech_service():
    """Returns a speech service for audio narration."""
    try:
        from tools.aos_speech_service import AOSSpeechService
        return AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
    except Exception:
        return GTTSService()


def _get_streaming_media_dir(output_dir: str | Path | None = None) -> Path:
    if output_dir:
        p = Path(output_dir).resolve()
    else:
        curr = Path(__file__).resolve()
        repo_root = None
        for parent in [curr, *curr.parents]:
            if (parent / "pyproject.toml").is_file() and (parent / "apps").is_dir():
                repo_root = parent
                break
        root = repo_root or Path.cwd()
        p = (root / "media" / "streaming").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def render_single_slide(
    slide_data: SlideData,
    output_dir: str | Path | None = None,
    quality: str = "low_quality",
) -> str:
    """Renders one SlideData object into a discrete MP4 file and returns its web path."""
    import shutil

    media_dir = _get_streaming_media_dir(output_dir)
    output_stem = f"slide_{slide_data.slide_num}"
    config.media_dir = str(media_dir)
    config.quality = quality
    config.output_file = output_stem

    class DynamicSlideScene(VoiceoverScene):
        def construct(self):
            try:
                self.set_speech_service(get_speech_service())
            except Exception as exc:
                print(f"[Voiceover] Service init warning: {exc}", file=sys.stderr)

            # Execution environment
            safe_globals: Dict[str, Any] = {
                "np": np,
                "MathTex": MathTex,
                "Text": Text,
                "VGroup": VGroup,
                "Group": Group,
                "Create": Create,
                "Write": Write,
                "Transform": Transform,
                "FadeIn": FadeIn,
                "FadeOut": FadeOut,
                "Line": Line,
                "Circle": Circle,
                "Square": Square,
                "Rectangle": Rectangle,
                "SurroundingRectangle": SurroundingRectangle,
                "Indicate": Indicate,
                "Arrow": Arrow,
                "Dot": Dot,
                "UP": UP,
                "DOWN": DOWN,
                "LEFT": LEFT,
                "RIGHT": RIGHT,
                "ORIGIN": ORIGIN,
                "BLUE": BLUE,
                "RED": RED,
                "YELLOW": YELLOW,
                "GREEN": GREEN,
                "WHITE": WHITE,
                "GRAY": GRAY,
            }
            safe_locals: Dict[str, Any] = {
                "self": self,
            }

            narration_text = slide_data.narration or f"Presenting slide {slide_data.slide_num}."

            try:
                with self.voiceover(text=narration_text) as tracker:
                    safe_locals["tracker"] = tracker
                    if slide_data.python_code.strip():
                        exec(slide_data.python_code, safe_globals, safe_locals)
                    else:
                        placeholder = Text(f"Slide {slide_data.slide_num}").scale(1.2)
                        self.play(FadeIn(placeholder), run_time=1.0)
            except Exception as exc:
                print(f"[Execution Error] Slide {slide_data.slide_num}: {exc}", file=sys.stderr)
                # Fallback hold so video compiles without crash
                self.wait(1.5)

    scene = DynamicSlideScene()
    scene.render()

    # Locate the generated MP4 file
    expected_mp4: Path | None = None
    for mp4 in media_dir.rglob(f"*{output_stem}*.mp4"):
        if mp4.is_file() and "partial_movie_files" not in mp4.parts:
            expected_mp4 = mp4
            break

    dest = media_dir / f"{output_stem}.mp4"
    if expected_mp4 and expected_mp4.is_file():
        if expected_mp4.resolve() != dest.resolve():
            try:
                shutil.copy2(expected_mp4, dest)
            except Exception:
                pass
        return f"/media/streaming/{output_stem}.mp4"

    # Fallback to the latest non-partial mp4 in the directory
    candidates = [
        p for p in media_dir.rglob("*.mp4")
        if p.is_file() and "partial_movie_files" not in p.parts
    ]
    if candidates:
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        if latest.resolve() != dest.resolve():
            try:
                shutil.copy2(latest, dest)
            except Exception:
                pass
        return f"/media/streaming/{output_stem}.mp4"

    return f"/media/streaming/{output_stem}.mp4"


def render_branding_intro_video(output_dir: str | Path | None = None) -> str:
    """Renders the 16s RUKUMINI branding intro compute buffer to intro.mp4."""
    import shutil

    media_dir = _get_streaming_media_dir(output_dir)
    dest = media_dir / "intro.mp4"

    if dest.is_file():
        return "/media/streaming/intro.mp4"

    config.media_dir = str(media_dir)
    config.quality = "low_quality"
    config.output_file = "intro"

    class BrandingIntroScene(Scene):
        def construct(self):
            assets_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "agents", "tools", "assets")
            )
            rukumini_logo_path = os.path.join(assets_dir, "rukumini.png")
            college_logo_path = os.path.join(assets_dir, "college_logo.png")

            if os.path.exists(rukumini_logo_path):
                logo = ImageMobject(rukumini_logo_path).scale(0.85)
            else:
                logo = Text("RUKUMINI", font_size=60, weight=BOLD, color="#C41E3A")

            subtext = Text("Agentic Educational Lecture System", font_size=24, color=GRAY)
            subtext.next_to(logo, DOWN, buff=0.4)

            self.play(FadeIn(logo, shift=UP * 0.4), FadeIn(subtext), run_time=1.5)
            self.wait(1.5)

            if os.path.exists(college_logo_path):
                college_logo = ImageMobject(college_logo_path).scale(0.5).to_corner(DR, buff=0.6)
                self.play(FadeIn(college_logo, shift=LEFT * 0.3), run_time=1.0)
                self.wait(1.2)
                self.play(FadeOut(logo), FadeOut(subtext), FadeOut(college_logo), run_time=1.0)
            else:
                self.play(FadeOut(logo), FadeOut(subtext), run_time=1.0)

    scene = BrandingIntroScene()
    scene.render()

    for p in media_dir.rglob("*intro*.mp4"):
        if p.is_file() and "partial_movie_files" not in p.parts:
            if p.resolve() != dest.resolve():
                try:
                    shutil.copy2(p, dest)
                except Exception:
                    pass
            return "/media/streaming/intro.mp4"

    return "/media/streaming/intro.mp4"

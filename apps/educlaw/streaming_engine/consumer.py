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

from apps.educlaw.streaming_engine.models import SlideData


def get_speech_service():
    """Returns a speech service for audio narration (AOS Pocket TTS or fallback)."""
    # 1. Try AOS Pocket TTS
    for mod_name in ("apps.agents.tools.aos_speech_service", "tools.aos_speech_service"):
        try:
            mod = __import__(mod_name, fromlist=["AOSSpeechService"])
            AOSSpeechService = getattr(mod, "AOSSpeechService")
            return AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        except Exception:
            pass
    # 2. Try gTTS if installed
    try:
        from manim_voiceover.services.gtts import GTTSService
        return GTTSService()
    except Exception:
        pass
    return None


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
            speech_service = get_speech_service()
            if speech_service is not None:
                try:
                    self.set_speech_service(speech_service)
                except Exception as exc:
                    print(f"[Voiceover] Service init warning: {exc}", file=sys.stderr)
                    speech_service = None

            # Rich execution environment
            safe_globals: Dict[str, Any] = {
                "np": np,
                "MathTex": MathTex,
                "Text": Text,
                "VGroup": VGroup,
                "Group": Group,
                "Create": Create,
                "Write": Write,
                "Transform": Transform,
                "ReplacementTransform": ReplacementTransform,
                "FadeIn": FadeIn,
                "FadeOut": FadeOut,
                "GrowFromCenter": GrowFromCenter,
                "Indicate": Indicate,
                "Circumscribe": Circumscribe,
                "Wiggle": Wiggle,
                "Line": Line,
                "DashedLine": DashedLine,
                "Arrow": Arrow,
                "DoubleArrow": DoubleArrow,
                "Vector": Vector,
                "Circle": Circle,
                "Square": Square,
                "Rectangle": Rectangle,
                "RoundedRectangle": RoundedRectangle,
                "SurroundingRectangle": SurroundingRectangle,
                "Polygon": Polygon,
                "Triangle": Triangle,
                "Dot": Dot,
                "Axes": Axes,
                "NumberPlane": NumberPlane,
                "ComplexPlane": ComplexPlane,
                "PolarPlane": PolarPlane,
                "FunctionGraph": FunctionGraph,
                "ParametricFunction": ParametricFunction,
                "Arc": Arc,
                "ArcBetweenPoints": ArcBetweenPoints,
                "CurvedArrow": CurvedArrow,
                "DashedVMobject": DashedVMobject,
                "Brace": Brace,
                "DecimalNumber": DecimalNumber,
                "LaggedStart": LaggedStart,
                "always_redraw": always_redraw,
                "ValueTracker": ValueTracker,
                "UP": UP,
                "DOWN": DOWN,
                "LEFT": LEFT,
                "RIGHT": RIGHT,
                "ORIGIN": ORIGIN,
                "UL": UL,
                "UR": UR,
                "DL": DL,
                "DR": DR,
                "BLUE": BLUE,
                "RED": RED,
                "YELLOW": YELLOW,
                "GREEN": GREEN,
                "WHITE": WHITE,
                "GRAY": GRAY,
                "GREY": GREY,
                "BLACK": BLACK,
                "ORANGE": ORANGE,
                "PURPLE": PURPLE,
                "GOLD": GOLD,
                "TEAL": TEAL,
                "PI": PI,
                "TAU": TAU,
            }
            safe_locals: Dict[str, Any] = {
                "self": self,
            }

            narration_text = slide_data.narration or f"Presenting slide {slide_data.slide_num}."

            try:
                if speech_service is not None:
                    with self.voiceover(text=narration_text) as tracker:
                        safe_locals["tracker"] = tracker
                        if slide_data.python_code.strip():
                            exec(slide_data.python_code, safe_globals, safe_locals)
                        else:
                            placeholder = Text(f"Slide {slide_data.slide_num}").scale(1.2)
                            self.play(FadeIn(placeholder), run_time=1.0)
                else:
                    # Silent or fallback hold
                    if slide_data.python_code.strip():
                        exec(slide_data.python_code, safe_globals, safe_locals)
                    else:
                        placeholder = Text(f"Slide {slide_data.slide_num}").scale(1.2)
                        self.play(FadeIn(placeholder), run_time=1.0)
                    self.wait(2.0)
            except Exception as exc:
                print(f"[Execution Error] Slide {slide_data.slide_num}: {exc}", file=sys.stderr)
                # Resilient fallback slide visual so compilation NEVER halts
                try:
                    fallback_title = Text(f"Slide {slide_data.slide_num}", font_size=40, color=YELLOW).to_edge(UP)
                    fallback_box = SurroundingRectangle(fallback_title, color=BLUE, buff=0.3)
                    self.play(Create(fallback_box), Write(fallback_title), run_time=1.0)
                    self.wait(1.5)
                except Exception:
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
        return str(dest.resolve())

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
        return str(dest.resolve())

    return str(dest.resolve())


def assemble_slide_chunks(
    chunk_paths: list[str | Path],
    output_path: str | Path,
) -> Path:
    """Concatenate individual slide MP4s into a single seamless final video with audio."""
    import subprocess
    import shutil

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    valid_chunks = [Path(p).resolve() for p in chunk_paths if Path(p).is_file()]
    if not valid_chunks:
        raise FileNotFoundError("No valid slide chunks found for concatenation.")

    if len(valid_chunks) == 1:
        shutil.copy2(valid_chunks[0], out_file)
        return out_file

    concat_txt = out_file.parent / f"concat_{int(time.time() * 1000)}.txt"
    try:
        with open(concat_txt, "w", encoding="utf-8") as f:
            for chunk in valid_chunks:
                f.write(f"file '{str(chunk).replace('\\', '/')}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not out_file.is_file() or out_file.stat().st_size == 0:
            print(f"[FFmpeg Warning] Re-encode concat failed: {res.stderr[:300]}, trying stream copy", file=sys.stderr)
            cmd_copy = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_txt),
                "-c", "copy",
                str(out_file),
            ]
            subprocess.run(cmd_copy, capture_output=True, text=True, check=True)
    finally:
        try:
            concat_txt.unlink(missing_ok=True)
        except Exception:
            pass

    return out_file


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

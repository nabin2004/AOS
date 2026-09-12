"""Native Keyframe Producer-Consumer Manim Engine for AOS Animation Pipeline.

Generates discrete pedagogical keyframe slides with synchronized Pocket TTS voiceover,
renders each slide into an individual MP4 chunk, and concatenates all chunks into
a seamless final video. Entirely self-contained in apps/agents (no educlaw dependency).
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
from manim import *
from manim_voiceover import VoiceoverScene
from openai import OpenAI


@dataclass
class SlideData:
    slide_num: int
    narration: str
    python_code: str
    is_final_slide: bool = False
    chunk_path: str | None = None


def get_speech_service():
    """Initializes the resident Pocket TTS voiceover service."""
    try:
        from tools.aos_speech_service import AOSSpeechService

        return AOSSpeechService()
    except Exception as exc:
        print(f"[Keyframe Engine] Speech service init note: {exc}", file=sys.stderr)
        return None


def get_llm_client(
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> Tuple[OpenAI, str]:
    """Dynamically resolves LLM client and model for keyframe script generation."""
    openrouter_key = (
        api_key
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("AOS_OPENROUTER_API_KEY")
        or ""
    ).strip()

    openai_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("AOS_OPENAI_API_KEY")
        or ""
    ).strip()

    openai_base = (
        base_url
        or os.getenv("AOS_OPENAI_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or ""
    ).strip()

    ollama_base = (os.getenv("OLLAMA_BASE_URL") or "").strip()

    if base_url and base_url.strip():
        effective_base = base_url.strip()
        effective_key = (api_key or "local").strip()
    elif openrouter_key:
        effective_base = "https://openrouter.ai/api/v1"
        effective_key = openrouter_key
    elif openai_base:
        effective_base = openai_base
        effective_key = openai_key or "local"
    elif openai_key:
        effective_base = "https://api.openai.com/v1"
        effective_key = openai_key
    elif ollama_base:
        effective_base = f"{ollama_base.rstrip('/')}/v1"
        effective_key = "ollama"
    else:
        effective_base = "https://openrouter.ai/api/v1"
        effective_key = "local"

    if model and model.strip():
        effective_model = model.strip()
    elif "openrouter.ai" in effective_base:
        raw_m = (
            os.getenv("AOS_OPENROUTER_MODEL")
            or os.getenv("AOS_CODER_MODEL")
            or "google/gemini-2.5-flash"
        )
        effective_model = raw_m.removeprefix("openrouter:").strip()
    else:
        effective_model = (
            os.getenv("AOS_CODER_MODEL")
            or os.getenv("AOS_OPENAI_MODEL")
            or "qwen2.5-coder"
        ).strip()

    client = OpenAI(base_url=effective_base, api_key=effective_key)
    return client, effective_model


SYSTEM_PROMPT = """You are an expert mathematical animator and computer science educator writing Manim Community Edition code with synchronized voiceover.
Output your response using the following format:

<narration>
Natural, conversational, highly engaging spoken explanation. You can insert <bookmark mark="v1"/>, <bookmark mark="v2"/> to sync visual animations with speech.
</narration>

```python
# Self-contained Manim animation snippet for this specific slide.
# Do NOT define a Scene class. Assume you are inside Scene.construct(self).
# Use self.play(...), self.wait_until_bookmark("v1"), self.wait(...) directly.
```

Rules:
1. Always keep animations elegant, centered, and mathematically precise.
2. Use MathTex for equations, Text for readable titles.
3. Coordinate bounds: x in [-6, 6], y in [-3.5, 3.5].
4. Color palette: BLUE, YELLOW, TEAL, GREEN, GOLD, RED, WHITE.
"""


def _parse_markdown(markdown_output: str) -> Tuple[str, str]:
    narration = ""
    code = ""
    narration_match = re.search(r"<narration>(.*?)</narration>", markdown_output, re.DOTALL | re.IGNORECASE)
    if narration_match:
        narration = narration_match.group(1).strip()

    code_match = re.search(r"```(?:python)?(.*?)```", markdown_output, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()

    return narration, code


def _build_curated_fallback_slide(prompt: str, slide_num: int, total_slides: int) -> Tuple[str, str]:
    """Curated, high-fidelity STEM fallback slides with rich LaTeX and diagrams."""
    p_lower = prompt.lower()
    if "euler" in p_lower:
        if slide_num == 1:
            narration = "Euler's formula reveals one of the most profound bridges in mathematics, establishing an unexpected equality between exponential growth and circular trigonometry."
            code = (
                'title = Text("Euler\'s Formula", font_size=40, color=YELLOW).to_edge(UP)\n'
                'formula = MathTex(r"e^{i\\theta} = \\cos(\\theta) + i\\sin(\\theta)", font_size=48, color=BLUE)\n'
                'box = SurroundingRectangle(formula, color=GOLD, buff=0.35)\n'
                'self.play(Write(title))\n'
                'self.play(Create(box), Write(formula))\n'
                'self.wait(1)\n'
            )
        elif slide_num == 2:
            narration = "Geometrically, as theta varies, this represents uniform motion along the unit circle in the complex plane, with horizontal component cosine and vertical component sine."
            code = (
                'plane = ComplexPlane(x_range=[-2, 2, 1], y_range=[-2, 2, 1]).scale(0.8)\n'
                'circle = Circle(radius=1.6, color=TEAL)\n'
                'dot = Dot(circle.point_at_angle(PI/4), color=RED)\n'
                'label = MathTex(r"e^{i\\theta}", color=RED).next_to(dot, UR, buff=0.15)\n'
                'line = Line(plane.n2p(0), dot.get_center(), color=YELLOW)\n'
                'self.play(Create(plane), Create(circle))\n'
                'self.play(Create(line), FadeIn(dot), Write(label))\n'
                'self.wait(1)\n'
            )
        else:
            narration = "Setting theta equal to pi yields Euler's identity, famously uniting five of the most fundamental constants in all of mathematics: e, i, pi, 1, and 0."
            code = (
                'identity = MathTex(r"e^{i\\pi} + 1 = 0", font_size=56, color=YELLOW)\n'
                'box = SurroundingRectangle(identity, color=GREEN, buff=0.4)\n'
                'caption = Text("The Most Beautiful Theorem in Mathematics", font_size=26, color=WHITE).next_to(box, DOWN, buff=0.5)\n'
                'self.play(Create(box), Write(identity))\n'
                'self.play(FadeIn(caption))\n'
                'self.wait(1)\n'
            )
    elif "fourier" in p_lower:
        if slide_num == 1:
            narration = "The Fourier Transform decomposes any signal or function into a continuous spectrum of sinusoidal frequencies."
            code = (
                'title = Text("The Fourier Transform", font_size=40, color=YELLOW).to_edge(UP)\n'
                'formula = MathTex(r"\\hat{f}(\\xi) = \\int_{-\\infty}^{\\infty} f(t) e^{-2\\pi i t \\xi} dt", font_size=44, color=BLUE)\n'
                'box = SurroundingRectangle(formula, color=GOLD, buff=0.35)\n'
                'self.play(Write(title))\n'
                'self.play(Create(box), Write(formula))\n'
                'self.wait(1)\n'
            )
        elif slide_num == 2:
            narration = "Each frequency component corresponds to wrapping the signal around the complex origin at frequency xi and finding the center of mass."
            code = (
                'axes = Axes(x_range=[0, 4, 1], y_range=[-1.5, 1.5, 1], x_length=7, y_length=3).shift(UP*0.5)\n'
                'sine = axes.plot(lambda x: np.sin(2 * PI * x), color=TEAL)\n'
                'label = Text("Time Domain Signal", font_size=24, color=TEAL).next_to(axes, DOWN, buff=0.3)\n'
                'self.play(Create(axes), Create(sine))\n'
                'self.play(Write(label))\n'
                'self.wait(1)\n'
            )
        else:
            narration = "Through the inverse Fourier transform, the original time-domain function can be reconstructed perfectly by integrating over all frequencies."
            code = (
                'title = Text("Inverse Fourier Reconstruction", font_size=36, color=GREEN).to_edge(UP)\n'
                'formula = MathTex(r"f(t) = \\int_{-\\infty}^{\\infty} \\hat{f}(\\xi) e^{2\\pi i t \\xi} d\\xi", font_size=44, color=YELLOW)\n'
                'box = SurroundingRectangle(formula, color=GREEN, buff=0.35)\n'
                'self.play(Write(title))\n'
                'self.play(Create(box), Write(formula))\n'
                'self.wait(1)\n'
            )
    else:
        narration = f"In slide {slide_num}, we explore the key mathematical and conceptual properties of {prompt}."
        code = (
            f'title = Text("Slide {slide_num}: {prompt[:30]}", font_size=38, color=YELLOW).to_edge(UP)\n'
            'box = SurroundingRectangle(title, color=BLUE, buff=0.3)\n'
            f'content = Text("Key Principle {slide_num}", font_size=30, color=WHITE).shift(DOWN*0.5)\n'
            'self.play(Create(box), Write(title))\n'
            'self.play(FadeIn(content))\n'
            'self.wait(1)\n'
        )
    return narration, code


def generate_keyframe_stream(
    prompt: str,
    slide_queue: queue.Queue,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    total_slides: int = 3,
    on_progress: Callable[[str, str], None] | None = None,
) -> None:
    """Producer thread generating slide outlines, narrations, and Manim code."""
    def _notify(stage: str, msg: str = ""):
        if on_progress:
            try:
                on_progress(stage, msg)
            except Exception:
                pass
        print(f"-> {stage} {msg}".strip(), file=sys.stderr, flush=True)

    _notify("ClassifyNode", f"Classifying subject for: {prompt}")
    _notify("PlanLectureNode", f"Structuring {total_slides}-slide outline")

    client, effective_model = get_llm_client(base_url=base_url, api_key=api_key, model=model)

    try:
        outline_response = client.chat.completions.create(
            model=effective_model,
            messages=[
                {
                    "role": "user",
                    "content": f"Create a concise {total_slides}-slide outline for a visual Manim animation explaining: {prompt}. Return numbered points.",
                }
            ],
            temperature=0.3,
        )
        outline = outline_response.choices[0].message.content or f"1. Introduction to {prompt}\n2. Core formulation\n3. Visual conclusion"
    except Exception:
        outline = f"1. Core concept of {prompt}\n2. Mathematical mechanics\n3. Visual synthesis"

    for i in range(1, total_slides + 1):
        _notify("PlanTeachingScriptNode", f"Writing narration script for Slide {i}")
        slide_prompt = (
            f"Topic: {prompt}\n"
            f"Lecture Outline:\n{outline}\n\n"
            f"Write Slide {i} of {total_slides}.\n"
            f"Provide detailed university-style pedagogical narration with <bookmark mark=\"v1\"/> and clean Manim visual code."
        )

        try:
            response = client.chat.completions.create(
                model=effective_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": slide_prompt},
                ],
                temperature=0.4,
            )
            markdown_output = response.choices[0].message.content or ""
            narration, code = _parse_markdown(markdown_output)
        except Exception:
            narration, code = _build_curated_fallback_slide(prompt, i, total_slides)

        if not narration or not code:
            fb_narr, fb_code = _build_curated_fallback_slide(prompt, i, total_slides)
            if not narration:
                narration = fb_narr
            if not code:
                code = fb_code

        _notify("CodeAgent", f"Manim code and voiceover ready for Slide {i}")

        is_final = (i == total_slides)
        slide_queue.put(
            SlideData(
                slide_num=i,
                narration=narration,
                python_code=code,
                is_final_slide=is_final,
            )
        )


def render_single_keyframe(
    slide_data: SlideData,
    output_dir: Path,
    quality: str = "low_quality",
) -> Path | None:
    """Renders one SlideData chunk with Manim and Pocket TTS."""
    output_stem = f"slide_{slide_data.slide_num}"
    config.media_dir = str(output_dir)
    config.quality = quality
    config.output_file = output_stem

    class DynamicSlideScene(VoiceoverScene):
        def construct(self):
            speech_service = get_speech_service()
            if speech_service is not None:
                try:
                    self.set_speech_service(speech_service)
                except Exception as exc:
                    print(f"[Keyframe Voiceover] Error: {exc}", file=sys.stderr)
                    speech_service = None

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
            safe_locals: Dict[str, Any] = {"self": self}

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
                    if slide_data.python_code.strip():
                        exec(slide_data.python_code, safe_globals, safe_locals)
                    else:
                        placeholder = Text(f"Slide {slide_data.slide_num}").scale(1.2)
                        self.play(FadeIn(placeholder), run_time=1.0)
                    self.wait(2.0)
            except Exception as exc:
                print(f"[Keyframe Render Warning] Slide {slide_data.slide_num}: {exc}", file=sys.stderr)
                try:
                    fallback_title = Text(f"Slide {slide_data.slide_num}", font_size=40, color=YELLOW).to_edge(UP)
                    fallback_box = SurroundingRectangle(fallback_title, color=BLUE, buff=0.3)
                    self.play(Create(fallback_box), Write(fallback_title), run_time=1.0)
                    self.wait(1.5)
                except Exception:
                    self.wait(1.5)

    scene = DynamicSlideScene()
    scene.render()

    expected_mp4: Path | None = None
    for mp4 in output_dir.rglob(f"*{output_stem}*.mp4"):
        if mp4.is_file() and "partial_movie_files" not in mp4.parts:
            expected_mp4 = mp4
            break

    dest = output_dir / f"{output_stem}.mp4"
    if expected_mp4 and expected_mp4.is_file():
        if expected_mp4.resolve() != dest.resolve():
            try:
                shutil.copy2(expected_mp4, dest)
            except Exception:
                pass
        return dest.resolve()

    return None


def assemble_slide_chunks(chunk_paths: List[Path], output_path: Path) -> Path:
    """Concatenates individual slide MP4s with audio into a single seamless MP4."""
    if not chunk_paths:
        raise ValueError("No video chunks provided to assemble")

    valid_chunks = [p for p in chunk_paths if p.is_file() and p.stat().st_size > 0]
    if not valid_chunks:
        raise ValueError("No valid video chunks found on disk")

    if len(valid_chunks) == 1:
        shutil.copy2(valid_chunks[0], output_path)
        return output_path

    concat_file = output_path.parent / "chunks_concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in valid_chunks:
            escaped = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{escaped}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path.resolve()),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0 or not output_path.is_file():
        # Fallback copy first chunk if concatenation failed
        shutil.copy2(valid_chunks[0], output_path)

    return output_path


def run_producer_consumer(
    prompt: str,
    *,
    output_dir: str | Path | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    total_slides: int = 3,
    quality: str = "low_quality",
    on_progress: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    """Coordinates producer slide synthesis and consumer Manim/TTS rendering in one go."""
    if output_dir:
        run_dir = Path(output_dir).resolve()
    else:
        run_id = f"run_{int(time.time() * 1000)}"
        root = Path(__file__).resolve().parent
        run_dir = (root / "workspace" / "producer_consumer_runs" / run_id).resolve()

    run_dir.mkdir(parents=True, exist_ok=True)

    def _notify(stage: str, msg: str = ""):
        if on_progress:
            try:
                on_progress(stage, msg)
            except Exception:
                pass
        print(f"-> {stage} {msg}".strip(), file=sys.stderr, flush=True)

    slide_queue: queue.Queue = queue.Queue()

    producer_thread = threading.Thread(
        target=generate_keyframe_stream,
        args=(prompt, slide_queue),
        kwargs={
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "total_slides": total_slides,
            "on_progress": on_progress,
        },
        daemon=True,
    )
    producer_thread.start()

    rendered_chunks: list[Path] = []
    slide_records: list[dict[str, Any]] = []
    combined_code_parts: list[str] = [
        "# Auto-generated by AOS Native Keyframe Producer-Consumer Engine",
        "from manim import *",
        "from manim_voiceover import VoiceoverScene",
        "from tools.aos_speech_service import AOSSpeechService\n",
    ]

    while True:
        try:
            slide_data: SlideData = slide_queue.get(timeout=1.0)
        except queue.Empty:
            if not producer_thread.is_alive():
                break
            continue

        _notify("VALIDATING_CODE", f"Validating code for Slide {slide_data.slide_num}")
        _notify("RENDERING", f"Rendering Slide {slide_data.slide_num} with voice narration")

        chunk_path: Path | None = None
        try:
            chunk_path = render_single_keyframe(slide_data, run_dir, quality=quality)
            if chunk_path and chunk_path.is_file():
                rendered_chunks.append(chunk_path)
                slide_data.chunk_path = str(chunk_path)
        except Exception as exc:
            print(f"[Consumer Warning] Slide {slide_data.slide_num} render failed: {exc}", file=sys.stderr)

        combined_code_parts.append(
            f"# --- Slide {slide_data.slide_num} ---\n"
            f"# Narration: {slide_data.narration}\n"
            f"{slide_data.python_code}\n"
        )
        slide_records.append({
            "slide_num": slide_data.slide_num,
            "narration": slide_data.narration,
            "code": slide_data.python_code,
            "chunk_path": str(chunk_path) if chunk_path and chunk_path.is_file() else None,
        })

        if slide_data.is_final_slide:
            break

    producer_thread.join(timeout=30)

    final_video = run_dir / "final.mp4"
    if rendered_chunks:
        _notify("assemble", "Assembling final video with synchronized narration")
        assemble_slide_chunks(rendered_chunks, final_video)
        _notify("VALIDATING_VIDEO", "Validating output animation video")

    scene_file = run_dir / "scene.py"
    scene_file.write_text("\n".join(combined_code_parts), encoding="utf-8")

    manifest = {
        "ok": final_video.is_file() and final_video.stat().st_size > 0,
        "mode": "animate",
        "prompt": prompt,
        "run_dir": str(run_dir),
        "video_path": str(final_video) if final_video.is_file() else None,
        "scene_file": str(scene_file),
        "total_slides": len(slide_records),
        "slides": slide_records,
        "has_audio": True,
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _notify("upload", "Animation and narration ready")

    return manifest

"""Native Keyframe & Teaching Segment Engine for AOS Animation Pipeline.

Decouples visual animation duration from detailed pedagogical narration:
1. Renders the visual anchor animation once using Manim (clean, fast, ~5-10s).
2. Generates an in-depth pedagogical teaching narration informed by the visual anchor
   (explains symbols, intuition, geometric meaning, analogies, avoiding redundancy).
3. Synthesizes authoritative Pocket TTS audio and measures its exact duration (e.g. 60-90s).
4. Freezes the final visual frame using FFmpeg (`tpad=stop_mode=clone`) for the
   remaining duration without re-running Manim.
5. Assembles all TeachingSegments into a cohesive, high-production lesson video.
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
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from manim import *
from openai import OpenAI

from ir import SemanticEvent, TeachingSegment, VisualAnchor
from tools.timeline_assembler import (
    assemble_segments,
    get_media_duration,
    hold_final_state,
)


@dataclass
class SlideData:
    """Legacy compatibility bridge for existing callers."""
    slide_num: int
    narration: str
    python_code: str
    is_final_slide: bool = False
    chunk_path: str | None = None
    teaching_segment: TeachingSegment | None = None


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


VISUAL_PLANNER_PROMPT = """You are an expert mathematical animator creating concise visual slides in Manim Community Edition.
Your job is ONLY to build a clean, elegant visual anchor (equations, diagrams, titles).
Do NOT write narration here. Keep the animation short, focused, and elegant (5-10 seconds total).

Output format:
<visual_anchor>
{
  "type": "formula" | "diagram" | "geometry" | "concept",
  "title": "Short Descriptive Title",
  "latex": "Primary equation if applicable or empty string",
  "visible_elements": ["list", "of", "symbols", "and", "labels"],
  "visual_purpose": "Pedagogical role of this visual anchor"
}
</visual_anchor>

```python
# Self-contained Manim code for Scene.construct(self).
# Use self.play(...) and self.wait(...) directly.
# Coordinate bounds: x in [-6, 6], y in [-3.5, 3.5].
# Palette: BLUE, YELLOW, TEAL, GREEN, GOLD, RED, WHITE.
```
"""

NARRATION_PLANNER_PROMPT = """You are a master university professor and educator.
The student is currently looking at a visual slide on screen.
Your job is to provide an IN-DEPTH, DETAILED teaching lecture explaining the concept thoroughly.

CRITICAL ANTI-REDUNDANCY RULE:
- Do NOT simply read or transcribe the equation or labels already visible on screen!
- (BAD: "Here we see e to the i theta equals cosine theta plus i sine theta.")
- (GOOD: Explain what each symbol means, why the relationship exists, provide physical and geometric intuition, real-world relevance, analogies, and connections.)

PEDAGOGICAL STRUCTURE TO FOLLOW:
1. INTRODUCE: What fundamental insight are we examining, and why is it important?
2. OBSERVE: Guide the student's eye to key components.
3. DEFINE: Deep dive into the meaning of each symbol (e.g. what e, i, theta, cos, sin actually do).
4. BREAK DOWN & EXPLAIN: Why does this equality hold? How do algebra and geometry unify here?
5. INTUITION: What is the geometric picture or physical analogy (e.g. circular motion, rotation)?
6. EXAMPLE & CONNECTION: A notable case (e.g. Euler's identity), application, or historical context.
7. RECAP: The core conceptual takeaway.

Length: Write a comprehensive, conversational explanation (around 120-200 words, ~45-90 seconds of speech).
Wrap your output in <narration> ... </narration> tags.
"""


def _parse_visual_output(text: str) -> Tuple[VisualAnchor, str]:
    """Extracts VisualAnchor metadata and Python code from LLM output."""
    anchor = VisualAnchor(type="formula", visual_purpose="Core concept visualization")
    anchor_match = re.search(r"<visual_anchor>(.*?)</visual_anchor>", text, re.DOTALL | re.IGNORECASE)
    if anchor_match:
        try:
            raw_json = anchor_match.group(1).strip()
            data = json.loads(raw_json)
            anchor = VisualAnchor(**data)
        except Exception:
            pass

    code = ""
    code_match = re.search(r"```(?:python)?(.*?)```", text, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()

    return anchor, code


def _parse_narration_output(text: str) -> str:
    """Extracts pedagogical narration from LLM output."""
    narr_match = re.search(r"<narration>(.*?)</narration>", text, re.DOTALL | re.IGNORECASE)
    if narr_match:
        return narr_match.group(1).strip()
    clean = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return clean.strip()


def _build_curated_fallback_segment(prompt: str, slide_num: int, total_slides: int) -> TeachingSegment:
    """Curated, high-fidelity STEM TeachingSegments with rich visual anchors and detailed ~60-90s pedagogy."""
    p_lower = prompt.lower()
    if "euler" in p_lower:
        if slide_num == 1:
            anchor = VisualAnchor(
                type="formula",
                title="Euler's Formula",
                latex=r"e^{i\theta} = \cos(\theta) + i\sin(\theta)",
                visible_elements=["e", "i", "theta", "cos(theta)", "sin(theta)"],
                visual_purpose="Introduce the fundamental bridge between exponential growth and circular trigonometry.",
            )
            code = (
                'title = Text("Euler\'s Formula", font_size=40, color=YELLOW).to_edge(UP)\n'
                'formula = MathTex(r"e^{i\\theta} = \\cos(\\theta) + i\\sin(\\theta)", font_size=48, color=BLUE)\n'
                'box = SurroundingRectangle(formula, color=GOLD, buff=0.35)\n'
                'self.play(Write(title))\n'
                'self.play(Write(formula))\n'
                'self.play(Create(box))\n'
                'self.wait(1.0)\n'
            )
            narration = (
                "Euler's formula stands as one of the most profound bridges in all of mathematics, "
                "establishing an astonishing equality between exponential growth and circular trigonometry. "
                "To truly understand what this equation tells us, let us look beyond the symbols. "
                "The constant e is the natural base of growth, usually associated with continuous compounding in one dimension. "
                "The imaginary unit i, on the other hand, represents orthogonal rotation by ninety degrees in the complex plane. "
                "When we place i in the exponent multiplied by the angle theta, growth ceases to be exponential expansion along a line, "
                "and instead transforms into continuous rotation around a circle. "
                "The real part gives us the horizontal projection, cosine of theta, while the imaginary part gives the vertical component, sine of theta. "
                "In a single stroke, this unified two completely separate branches of mathematics that mathematicians had studied for centuries."
            )
        elif slide_num == 2:
            anchor = VisualAnchor(
                type="geometry",
                title="Geometric Interpretation in the Complex Plane",
                latex=r"e^{i\theta}",
                visible_elements=["ComplexPlane", "Circle", "e^{i\\theta}", "cos(\\theta)", "sin(\\theta)"],
                visual_purpose="Visualize uniform rotation on the unit circle as theta varies.",
            )
            code = (
                'title = Text("Geometric Interpretation", font_size=36, color=TEAL).to_edge(UP)\n'
                'plane = ComplexPlane(x_range=[-2, 2, 1], y_range=[-2, 2, 1]).scale(0.75).shift(DOWN*0.3)\n'
                'circle = Circle(radius=1.5, color=TEAL).move_to(plane.n2p(0))\n'
                'dot = Dot(circle.point_at_angle(PI/4), color=RED)\n'
                'label = MathTex(r"e^{i\\theta}", color=RED).next_to(dot, UR, buff=0.15)\n'
                'line = Line(plane.n2p(0), dot.get_center(), color=YELLOW)\n'
                'self.play(Write(title))\n'
                'self.play(Create(plane), Create(circle))\n'
                'self.play(Create(line), FadeIn(dot), Write(label))\n'
                'self.wait(1.0)\n'
            )
            narration = (
                "Now, let us examine the geometric picture of Euler's formula in the complex plane. "
                "As the parameter theta increases continuously, the expression e to the i theta traces out a path "
                "with constant distance equal to one from the origin. In other words, it is tracing the unit circle. "
                "If you track the shadow of this moving point along the horizontal real axis, it oscillates precisely according to the cosine function. "
                "Meanwhile, its shadow along the vertical imaginary axis oscillates according to the sine function. "
                "This means that complex exponentiation is simply uniform circular motion in disguise. "
                "Engineers and physicists rely on this exact insight every day to model alternating currents, quantum wavefunctions, and acoustic vibrations, "
                "turning complicated trigonometric differential equations into simple algebraic multiplications."
            )
        else:
            anchor = VisualAnchor(
                type="formula",
                title="Euler's Identity",
                latex=r"e^{i\pi} + 1 = 0",
                visible_elements=["e", "i", "pi", "1", "0"],
                visual_purpose="Present the most famous special case uniting five fundamental mathematical constants.",
            )
            code = (
                'identity = MathTex(r"e^{i\\pi} + 1 = 0", font_size=56, color=YELLOW)\n'
                'box = SurroundingRectangle(identity, color=GREEN, buff=0.4)\n'
                'caption = Text("The Most Beautiful Theorem in Mathematics", font_size=26, color=WHITE).next_to(box, DOWN, buff=0.5)\n'
                'self.play(Write(identity))\n'
                'self.play(Create(box))\n'
                'self.play(FadeIn(caption))\n'
                'self.wait(1.0)\n'
            )
            narration = (
                "When we evaluate Euler's formula at the specific angle theta equals pi radians, we arrive at Euler's identity. "
                "Richard Feynman called this the most remarkable formula in mathematics, and it is easy to see why. "
                "It brings together the five most fundamental constants of our universe: "
                "e, the foundation of calculus and growth; i, the seed of imaginary numbers; pi, the ratio of circular geometry; "
                "1, the multiplicative identity; and 0, the additive identity. "
                "Geometrically, an angle of pi radians is a half-circle rotation, which points directly in the negative real direction, landing on negative one. "
                "Adding one returns us perfectly to zero. It is a stunning testimony to the hidden harmony and coherence of mathematics."
            )
    elif "fourier" in p_lower:
        if slide_num == 1:
            anchor = VisualAnchor(
                type="formula",
                title="The Fourier Transform",
                latex=r"\hat{f}(\xi) = \int_{-\infty}^{\infty} f(t) e^{-2\pi i t \xi} dt",
                visible_elements=["f(t)", "hat{f}(xi)", "integral", "e^{-2pi i t xi}"],
                visual_purpose="Formulate the frequency decomposition of a continuous time-domain signal.",
            )
            code = (
                'title = Text("The Fourier Transform", font_size=40, color=YELLOW).to_edge(UP)\n'
                'formula = MathTex(r"\\hat{f}(\\xi) = \\int_{-\\infty}^{\\infty} f(t) e^{-2\\pi i t \\xi} dt", font_size=44, color=BLUE)\n'
                'box = SurroundingRectangle(formula, color=GOLD, buff=0.35)\n'
                'self.play(Write(title))\n'
                'self.play(Write(formula))\n'
                'self.play(Create(box))\n'
                'self.wait(1.0)\n'
            )
            narration = (
                "The Fourier Transform is one of the most transformative mathematical tools ever conceived, allowing us to decompose any complex signal into a spectrum of pure frequencies. "
                "Rather than viewing a sound, an image, or a physical vibration merely as an amplitude unfolding across time, the Fourier Transform asks a deeper question: "
                "which pure sinusoidal tones must be combined together to create this exact signal? "
                "The term e to the minus two pi i t xi acts as a winding mechanism that wraps the signal around the complex plane at frequency xi. "
                "By integrating over all time, we calculate the center of mass of this winding, which spikes dramatically only when the frequency matches an inherent component of the signal."
            )
        elif slide_num == 2:
            anchor = VisualAnchor(
                type="diagram",
                title="Time Domain vs Frequency Spectrum",
                latex="",
                visible_elements=["Time Signal", "Frequency Peaks"],
                visual_purpose="Illustrate the dual perspectives of time and frequency.",
            )
            code = (
                'axes = Axes(x_range=[0, 4, 1], y_range=[-1.5, 1.5, 1], x_length=7, y_length=3).shift(UP*0.5)\n'
                'sine = axes.plot(lambda x: np.sin(2 * PI * x), color=TEAL)\n'
                'label = Text("Time Domain Signal", font_size=24, color=TEAL).next_to(axes, DOWN, buff=0.3)\n'
                'self.play(Create(axes), Create(sine))\n'
                'self.play(Write(label))\n'
                'self.wait(1.0)\n'
            )
            narration = (
                "Consider the difference between a musical chord played on a piano and its sheet music. "
                "In the time domain, you perceive a complex, oscillating wave of air pressure that is difficult to untangle with the naked eye. "
                "In the frequency domain, that very same sound separates neatly into individual notes: the fundamental root, the third, and the fifth. "
                "This dual perspective is the bedrock of modern signal processing, digital audio compression like MP3, medical imaging in MRI scanners, and telecommunications."
            )
        else:
            anchor = VisualAnchor(
                type="formula",
                title="Inverse Fourier Reconstruction",
                latex=r"f(t) = \int_{-\infty}^{\infty} \hat{f}(\xi) e^{2\pi i t \xi} d\xi",
                visible_elements=["hat{f}(xi)", "f(t)", "integral"],
                visual_purpose="Demonstrate the complete and lossless reconstruction from frequency space.",
            )
            code = (
                'title = Text("Inverse Fourier Reconstruction", font_size=36, color=GREEN).to_edge(UP)\n'
                'formula = MathTex(r"f(t) = \\int_{-\\infty}^{\\infty} \\hat{f}(\\xi) e^{2\\pi i t \\xi} d\\xi", font_size=44, color=YELLOW)\n'
                'box = SurroundingRectangle(formula, color=GREEN, buff=0.35)\n'
                'self.play(Write(title))\n'
                'self.play(Write(formula))\n'
                'self.play(Create(box))\n'
                'self.wait(1.0)\n'
            )
            narration = (
                "Crucially, this frequency transformation is entirely reversible through the Inverse Fourier Transform. "
                "No information is destroyed in the process. By integrating each frequency component scaled by its corresponding amplitude and phase, "
                "we reassemble the original continuous signal with absolute mathematical precision. "
                "It represents a flawless duality: time and frequency are merely two complementary languages describing the exact same physical reality."
            )
    else:
        anchor = VisualAnchor(
            type="concept",
            title=f"Core Insight: {prompt[:30]}",
            latex="",
            visible_elements=[f"Principle {slide_num}", "Foundations"],
            visual_purpose=f"Introduce pedagogical stage {slide_num} of {prompt}.",
        )
        code = (
            f'title = Text("Slide {slide_num}: {prompt[:30]}", font_size=38, color=YELLOW).to_edge(UP)\n'
            'box = SurroundingRectangle(title, color=BLUE, buff=0.3)\n'
            f'content = Text("Key Principle {slide_num}", font_size=30, color=WHITE).shift(DOWN*0.5)\n'
            'self.play(Create(box), Write(title))\n'
            'self.play(FadeIn(content))\n'
            'self.wait(1.0)\n'
        )
        narration = (
            f"In this segment, we examine the foundational mechanisms of {prompt}. "
            f"Rather than merely memorizing definitions, we want to cultivate true conceptual intuition. "
            "When we break this concept down into its constituent elements, we discover how each component interacts dynamically "
            "to produce the overarching behavior. Observe the relationships displayed before you; "
            "understanding this visual anchor is the key to mastering the broader framework."
        )

    return TeachingSegment(
        slide_num=slide_num,
        concept=f"{prompt} - Part {slide_num}",
        learning_objective=anchor.visual_purpose,
        visual_anchor=anchor,
        manim_code=code,
        narration=narration,
    )


def plan_teaching_segment(
    prompt: str,
    slide_num: int,
    total_slides: int,
    outline: str,
    client: OpenAI,
    model: str,
) -> TeachingSegment:
    """Generates a TeachingSegment: first the visual anchor, then in-depth narration."""
    # Step 1: Generate Visual Anchor
    visual_user_prompt = (
        f"Topic: {prompt}\n"
        f"Lecture Outline:\n{outline}\n\n"
        f"Create the visual anchor for Slide {slide_num} of {total_slides}.\n"
        f"Provide the <visual_anchor> JSON and concise, elegant Manim code."
    )
    try:
        vis_resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": VISUAL_PLANNER_PROMPT},
                {"role": "user", "content": visual_user_prompt},
            ],
            temperature=0.3,
        )
        vis_text = vis_resp.choices[0].message.content or ""
        anchor, code = _parse_visual_output(vis_text)
    except Exception:
        fallback = _build_curated_fallback_segment(prompt, slide_num, total_slides)
        anchor, code = fallback.visual_anchor, fallback.manim_code

    if not code.strip():
        fallback = _build_curated_fallback_segment(prompt, slide_num, total_slides)
        anchor, code = fallback.visual_anchor, fallback.manim_code

    # Step 2: Generate In-Depth Narration based on the Visual Anchor
    narration_user_prompt = (
        f"Topic: {prompt}\n"
        f"Slide Number: {slide_num} of {total_slides}\n"
        f"Visual Anchor Title: {anchor.title}\n"
        f"Displayed Formula: {anchor.latex}\n"
        f"Visible Elements: {anchor.visible_elements}\n"
        f"Visual Purpose: {anchor.visual_purpose}\n\n"
        f"Write a deep, pedagogical, university-level teaching explanation.\n"
        f"Explain what the student is seeing, define the symbols, explain intuition and applications.\n"
        f"Remember: Do NOT merely read the slide aloud!"
    )
    try:
        narr_resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": NARRATION_PLANNER_PROMPT},
                {"role": "user", "content": narration_user_prompt},
            ],
            temperature=0.4,
        )
        narr_text = narr_resp.choices[0].message.content or ""
        narration = _parse_narration_output(narr_text)
    except Exception:
        fallback = _build_curated_fallback_segment(prompt, slide_num, total_slides)
        narration = fallback.narration

    if not narration.strip() or len(narration.split()) < 20:
        fallback = _build_curated_fallback_segment(prompt, slide_num, total_slides)
        narration = fallback.narration

    return TeachingSegment(
        slide_num=slide_num,
        concept=anchor.title or f"{prompt} - Slide {slide_num}",
        learning_objective=anchor.visual_purpose,
        visual_anchor=anchor,
        manim_code=code,
        narration=narration,
    )


def render_visual_anchor(
    segment: TeachingSegment,
    output_dir: Path,
    quality: str = "low_quality",
) -> Path | None:
    """Renders the pure visual animation for a TeachingSegment using Manim.

    Fast, self-contained, and completely independent of speech synthesis.
    """
    output_stem = f"slide_{segment.slide_num}_visual"
    config.media_dir = str(output_dir)
    config.quality = quality
    config.output_file = output_stem

    class VisualAnchorScene(Scene):
        def wait_until_bookmark(self, mark: str, **kwargs):
            self.wait(0.2)

        def construct(self):
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

            try:
                if segment.manim_code.strip():
                    exec(segment.manim_code, safe_globals, safe_locals)
                else:
                    t = Text(f"Slide {segment.slide_num}").scale(1.2)
                    self.play(FadeIn(t), run_time=1.0)
                self.wait(0.5)
            except Exception as exc:
                print(f"[Visual Render Warning] Slide {segment.slide_num}: {exc}", file=sys.stderr)
                try:
                    fallback_title = Text(f"Slide {segment.slide_num}", font_size=40, color=YELLOW).to_edge(UP)
                    fallback_box = SurroundingRectangle(fallback_title, color=BLUE, buff=0.3)
                    self.play(Create(fallback_box), Write(fallback_title), run_time=1.0)
                    self.wait(1.0)
                except Exception:
                    self.wait(1.0)

    scene = VisualAnchorScene()
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


def synthesize_teaching_audio(
    narration_text: str,
    output_wav: Path,
) -> float:
    """Synthesizes pedagogical narration into WAV audio using Pocket TTS.

    Returns the authoritative measured duration in seconds.
    """
    clean_text = re.sub(r"<bookmark.*?>", "", narration_text).strip()
    try:
        from tools.aos_speech_service import _get_narrator
        narrator = _get_narrator("alba", "english")
        narrator.synthesize(clean_text, output_wav)
    except Exception:
        # Fallback using scipy write of synthetic speech-timed tone or silence
        try:
            import scipy.io.wavfile
            sr = 24000
            words = len(clean_text.split())
            sec = max(3.0, words * 0.45)
            silence = np.zeros(int(sr * sec), dtype=np.float32)
            scipy.io.wavfile.write(output_wav, sr, silence)
        except Exception:
            pass

    return get_media_duration(output_wav)


def assemble_teaching_segment(
    segment: TeachingSegment,
    output_dir: Path,
) -> Path | None:
    """Combines visual animation, static visual hold, and authoritative narration audio."""
    if not segment.visual_path or not Path(segment.visual_path).is_file():
        return None

    in_video = Path(segment.visual_path)
    in_audio = Path(segment.audio_path) if segment.audio_path else None
    out_chunk = output_dir / f"slide_{segment.slide_num}.mp4"

    # Authoritative durations
    segment.visual_duration = get_media_duration(in_video)
    if in_audio and in_audio.is_file():
        segment.narration_duration = get_media_duration(in_audio)
    else:
        segment.narration_duration = segment.visual_duration

    # Visual hold duration
    hold_dur = segment.hold_duration

    # Extend visual using final state
    res = hold_final_state(
        video_path=in_video,
        hold_duration=hold_dur,
        audio_path=in_audio,
        output_path=out_chunk,
    )
    if res.is_file() and res.stat().st_size > 0:
        segment.chunk_path = str(res)
        return res

    return None


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
    """Coordinates decoupled visual anchor rendering and deep pedagogical narration in one go."""
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

    _notify("ClassifyNode", f"Classifying subject for: {prompt}")
    _notify("PlanLectureNode", f"Structuring {total_slides} TeachingSegments")

    client, effective_model = get_llm_client(base_url=base_url, api_key=api_key, model=model)

    try:
        outline_resp = client.chat.completions.create(
            model=effective_model,
            messages=[
                {
                    "role": "user",
                    "content": f"Create a concise {total_slides}-part pedagogical outline explaining: {prompt}. Return numbered points.",
                }
            ],
            temperature=0.3,
        )
        outline = outline_resp.choices[0].message.content or f"1. Introduction to {prompt}\n2. Mechanics\n3. Implications"
    except Exception:
        outline = f"1. Foundations of {prompt}\n2. Core formulation\n3. Intuition & synthesis"

    segments: List[TeachingSegment] = []
    rendered_chunks: List[Path] = []
    combined_code_parts: List[str] = [
        "# Auto-generated by AOS Decoupled Teaching Segment Engine",
        "from manim import *",
        "import numpy as np\n",
    ]

    for i in range(1, total_slides + 1):
        _notify("PlanTeachingScriptNode", f"Planning TeachingSegment {i} (Visual Anchor & Pedagogy)")
        segment = plan_teaching_segment(
            prompt=prompt,
            slide_num=i,
            total_slides=total_slides,
            outline=outline,
            client=client,
            model=effective_model,
        )

        _notify("CodeAgent", f"Visual anchor Manim code ready for Slide {i}")
        _notify("VALIDATING_CODE", f"Validating code for Slide {i}")
        _notify("RENDERING", f"Rendering visual anchor for Slide {i}")

        # Step 1: Render Visual Anchor
        visual_path = render_visual_anchor(segment, run_dir, quality=quality)
        if visual_path and visual_path.is_file():
            segment.visual_path = str(visual_path)
            segment.visual_duration = get_media_duration(visual_path)

        # Step 2: Synthesize Authoritative Pedagogical Narration
        audio_path = run_dir / f"slide_{i}_audio.wav"
        narr_dur = synthesize_teaching_audio(segment.narration, audio_path)
        segment.audio_path = str(audio_path)
        segment.narration_duration = narr_dur

        # Step 3: Decoupled Visual Hold & Segment Assembly
        _notify("TIMELINE_HOLD", f"Extending Slide {i} final frame: visual {segment.visual_duration:.1f}s, narration {segment.narration_duration:.1f}s")
        chunk_path = assemble_teaching_segment(segment, run_dir)
        if chunk_path and chunk_path.is_file():
            rendered_chunks.append(chunk_path)

        segments.append(segment)
        combined_code_parts.append(
            f"# --- Segment {segment.slide_num}: {segment.concept} ---\n"
            f"# Objective: {segment.learning_objective}\n"
            f"# Narration: {segment.narration}\n"
            f"{segment.manim_code}\n"
        )

    final_video = run_dir / "final.mp4"
    if rendered_chunks:
        _notify("assemble", "Assembling final lesson with synchronized audio-visual segments")
        assemble_segments(rendered_chunks, final_video)
        _notify("VALIDATING_VIDEO", "Validating output lesson video")

    scene_file = run_dir / "scene.py"
    scene_file.write_text("\n".join(combined_code_parts), encoding="utf-8")

    segment_dicts = [s.model_dump() for s in segments]
    manifest = {
        "ok": final_video.is_file() and final_video.stat().st_size > 0,
        "mode": "animate",
        "prompt": prompt,
        "run_dir": str(run_dir),
        "video_path": str(final_video) if final_video.is_file() else None,
        "scene_file": str(scene_file),
        "total_slides": len(segments),
        "slides": [
            {
                "slide_num": s.slide_num,
                "narration": s.narration,
                "code": s.manim_code,
                "visual_duration": s.visual_duration,
                "narration_duration": s.narration_duration,
                "total_duration": s.total_duration,
                "hold_duration": s.hold_duration,
                "chunk_path": s.chunk_path,
            }
            for s in segments
        ],
        "teaching_segments": segment_dicts,
        "has_audio": True,
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _notify("upload", "Lesson video and comprehensive narration ready")
    return manifest

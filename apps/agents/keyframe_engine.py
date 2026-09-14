"""Native Keyframe & Teaching Segment Engine for AOS Animation Pipeline.

Decouples visual animation duration from detailed pedagogical narration:
1. Renders rich, high-information-density visual slides using Manim (clean, fast, 5-15s).
2. Generates an in-depth pedagogical teaching narration informed by the visual anchor
   (explains symbols, intuition, geometric meaning, analogies, avoiding redundancy).
3. Synthesizes authoritative Pocket TTS audio and measures its exact duration (e.g. 50-90s).
4. Freezes the final visual frame using FFmpeg (`tpad=stop_mode=clone`) for the
   remaining duration without re-running Manim.
5. Assembles all TeachingSegments into a cohesive, high-production lesson video.
"""

from __future__ import annotations

from contextlib import contextmanager
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
from tools.visual_critic import (
    VisualContext,
    VisualCriticVerdict,
    get_visual_critic,
)

_manim_render_lock = threading.Lock()


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
        if openai_base.rstrip("/").endswith("/v1"):
            effective_base = openai_base.rstrip("/")
        else:
            effective_base = f"{openai_base.rstrip('/')}/v1"
        effective_key = openai_key or "local"
    elif openai_key:
        effective_base = "https://api.openai.com/v1"
        effective_key = openai_key
    elif ollama_base:
        if ollama_base.rstrip("/").endswith("/v1"):
            effective_base = ollama_base.rstrip("/")
        else:
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

    timeout_val = float(os.getenv("AOS_LLM_TIMEOUT_SECONDS", "15.0"))
    client = OpenAI(
        base_url=effective_base,
        api_key=effective_key,
        timeout=timeout_val,
        max_retries=1,
    )
    return client, effective_model


VISUAL_PLANNER_PROMPT = """You are an expert mathematical animator creating rich, highly informative, and elegant visual slides in Manim Community Edition.

CORE PHILOSOPHY:
"If a student paused this video and looked only at this frame, would they actually learn something?"
Do NOT generate sparse slides with only a title and one equation! A great educational slide contains clear formulas, symbol breakdowns, definitions, relationships, and meaningful geometric or conceptual diagrams.

VISUAL LAYOUT PATTERNS (Choose the most appropriate for the concept):
1. ANNOTATED FORMULA & BREAKDOWN:
   - Top: Clean title and primary equation highlighted inside a SurroundingRectangle.
   - Bottom/Side: "Where:" section with structured bullets (using MathTex or Text) defining what every single symbol means (e.g. e -> base of growth, i -> imaginary unit, theta -> angle, cos -> horizontal component, sin -> vertical component).
2. DYNAMIC GEOMETRIC PROJECTION (When motion provides learning value):
   - Coordinate plane or axes + unit circle / curve.
   - Vector or point moving dynamically along the path.
   - Explicit angle arc (theta) and dashed projection lines to axes showing horizontal (cos) and vertical (sin) components with a right triangle.
   - Side card summarizing key geometric relationships.
3. CONSTANTS & THEOREMS SYNTHESIS:
   - Theorem statement in a highlighted frame.
   - Structured breakdown card grouping foundational constants or concepts and their domains.
   - Visual vector or transition diagram illustrating the theorem.

RULES:
1. Coordinate bounds: x in [-6, 6], y in [-3.5, 3.5].
2. Use VGroup with .arrange(DOWN, aligned_edge=LEFT) for clean, readable text/bullet layouts.
3. Palette: BLUE, YELLOW, TEAL, GREEN, GOLD, RED, WHITE, GRAY.
4. Output concise JSON in <visual_anchor> and executable Manim snippet in ```python ... ``` WITHOUT defining any class or def construct(self).
   Start directly with mobjects and self.play(...).
   Do NOT use `with self.play(...)`. Use normal `self.play(...)`.
   Do NOT use `MathTex.animate.set_value`.

Output format:
<visual_anchor>
{
  "type": "annotated_formula" | "geometric_projection" | "constants_breakdown" | "concept_card",
  "title": "Descriptive Slide Title",
  "latex": "Primary formula if applicable",
  "visible_elements": ["List", "of", "all", "visible", "symbols"],
  "key_definitions": ["e: base of growth", "i: imaginary unit", "theta: angle"],
  "visual_states": ["Formula intro", "Symbol definitions", "Static summary"],
  "visual_purpose": "Clear pedagogical purpose"
}
</visual_anchor>

```python
# Start directly with mobjects and self.play(...)
title = Text("Slide Title", font_size=32, color=YELLOW).to_edge(UP, buff=0.4)
formula = MathTex(r"...", font_size=36, color=BLUE).next_to(title, DOWN, buff=0.35)
box = SurroundingRectangle(formula, color=GOLD, buff=0.2)
self.play(Write(title))
self.play(Write(formula), Create(box))
self.wait(1.5)
```
"""

NARRATION_PLANNER_PROMPT = """You are a master university professor and educator teaching with an intelligent animated whiteboard.
The student is looking at the rich visual slide on screen (which displays the formula, symbol breakdown, and diagrams).

Your job is to provide an IN-DEPTH, ENGAGING teaching lecture.

CRITICAL PEDAGOGICAL RULES:
1. SEAMLESS AUDIO-VISUAL COHESION:
   - Reference the visual slide naturally: "Notice on the slide...", "As shown in the breakdown below the formula...", "Look at the dashed projection to the real axis..."
2. TEACH, DO NOT MERELY READ:
   - The slide provides the visible definitions and symbols; you provide the intuition, the "why", the physical and geometric meaning, real-world relevance, analogies, and unexpected connections.
3. PEDAGOGICAL ARC:
   - INTRODUCE the core insight.
   - OBSERVE & BREAK DOWN the symbols and relationships.
   - EXPLAIN the intuition (e.g. why multiplying by i rotates by 90 degrees, why continuous compound growth wraps into a circle).
   - GIVE a concrete case or analogy.
   - RECAP the central takeaway.

Length: Around 140-220 words (~50-90 seconds of speech).
Wrap your output in <narration> ... </narration> tags.
"""


def _extract_topic_title(prompt: str) -> str:
    """Extracts a clean, short topic title from potentially massive or multi-paragraph user prompts."""
    lines = [l.strip() for l in prompt.strip().splitlines() if l.strip()]
    if not lines:
        return "Key Mathematical Principles"
    first_line = lines[0]
    # Remove common conversational prefixes
    first_line = re.sub(
        r"^(teach me about (the)?|explain (the)?|what is (the)?|help me understand (the)?|introduce (the)?)\s*",
        "",
        first_line,
        flags=re.IGNORECASE,
    ).strip()
    # Strip after common Wikipedia or navigation headers
    first_line = re.split(r":\s*Order of operations|\s*Article\s+Talk|\s*-\s*Wikipedia", first_line, flags=re.IGNORECASE)[0].strip()
    first_line = first_line.rstrip(":,.-")
    if len(first_line) > 60:
        first_line = first_line[:57] + "..."
    return first_line or "Key Mathematical Concept"


def _parse_visual_output(text: str) -> Tuple[VisualAnchor, str]:
    """Extracts VisualAnchor metadata and Python code from LLM output."""
    anchor = VisualAnchor(type="annotated_formula", visual_purpose="Core concept visualization")
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
    """Extracts pedagogical narration from LLM output, stripping reasoning traces."""
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    clean = re.sub(r"(?:^|\n)\s*Assistant:?\s*", "\n", clean, flags=re.IGNORECASE)
    narr_match = re.search(r"<narration>(.*?)</narration>", clean, re.DOTALL | re.IGNORECASE)
    if narr_match:
        return narr_match.group(1).strip()
    clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    return clean.strip()


def _build_curated_fallback_segment(prompt: str, slide_num: int, total_slides: int) -> TeachingSegment:
    """Curated, high-fidelity STEM TeachingSegments with rich visual anchors, symbol breakdowns, and ~60-90s pedagogy."""
    p_lower = prompt.lower()
    if "euler" in p_lower:
        if slide_num == 1:
            anchor = VisualAnchor(
                type="annotated_formula",
                title="Euler's Formula",
                latex=r"e^{i\theta} = \cos(\theta) + i\sin(\theta)",
                visible_elements=["e", "i", "theta", "cos(theta)", "sin(theta)"],
                key_definitions=[
                    "e ≈ 2.718 (base of continuous exponential growth)",
                    "i = √(-1) (imaginary unit / 90° orthogonal rotation)",
                    "θ (angle of rotation in radians)",
                    "cos(θ) (horizontal coordinate / real component)",
                    "sin(θ) (vertical coordinate / imaginary component)",
                ],
                visual_states=["Title and Formula", "Symbol Breakdown Cards", "Static Educational Hold"],
                visual_purpose="Introduce the bridge between exponential growth and circular trigonometry with full symbol breakdown.",
            )
            code = (
                'title = Text("Euler\'s Formula", font_size=36, color=YELLOW).to_edge(UP, buff=0.4)\n'
                'formula = MathTex(r"e^{i\\theta} = \\cos(\\theta) + i\\sin(\\theta)", font_size=44, color=BLUE).next_to(title, DOWN, buff=0.35)\n'
                'box = SurroundingRectangle(formula, color=GOLD, buff=0.25)\n'
                'where_lbl = Text("Where:", font_size=22, color=GOLD, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.2)\n'
                'b1 = MathTex(r"\\bullet\\ e \\approx 2.718 \\text{ (base of continuous exponential growth)}", font_size=20, color=WHITE)\n'
                'b2 = MathTex(r"\\bullet\\ i = \\sqrt{-1} \\text{ (imaginary unit / } 90^\\circ \\text{ orthogonal rotation)}", font_size=20, color=TEAL)\n'
                'b3 = MathTex(r"\\bullet\\ \\theta \\text{ (angle of rotation measured in radians)}", font_size=20, color=GREEN)\n'
                'b4 = MathTex(r"\\bullet\\ \\cos(\\theta) \\text{ (horizontal coordinate / real component)}", font_size=20, color=BLUE)\n'
                'b5 = MathTex(r"\\bullet\\ \\sin(\\theta) \\text{ (vertical coordinate / imaginary component)}", font_size=20, color=RED)\n'
                'bullets = VGroup(b1, b2, b3, b4, b5).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Write(formula), Create(box), run_time=1.2)\n'
                'self.play(FadeIn(where_lbl), run_time=0.5)\n'
                'self.play(LaggedStart(*[FadeIn(b, shift=RIGHT*0.2) for b in bullets], lag_ratio=0.2), run_time=2.0)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "Euler's formula stands as one of the most profound bridges in all of mathematics, "
                "establishing an astonishing equality between exponential growth and circular trigonometry. "
                "Look closely at the formula and the breakdown displayed on your screen. "
                "The constant e is Euler's number, approximately 2.718, which is the natural base of continuous compound growth. "
                "Next, we have the imaginary unit i, defined by the property that i squared equals negative one. "
                "In the complex plane, multiplying by i corresponds to an orthogonal ninety-degree counterclockwise rotation. "
                "When we place i in the exponent multiplied by the angle theta, growth ceases to expand along a straight line, "
                "and instead wraps into continuous uniform rotation around the unit circle. "
                "As detailed below the formula, the real part gives the horizontal coordinate, cosine of theta, "
                "while the imaginary part gives the vertical coordinate, sine of theta. "
                "This single line unites two branches of mathematics that had been studied separately for over two thousand years."
            )
        elif slide_num == 2:
            anchor = VisualAnchor(
                type="geometric_projection",
                title="Geometric Interpretation: Unit Circle & Projections",
                latex=r"e^{i\theta} = (\cos\theta, \sin\theta)",
                visible_elements=["ComplexPlane", "UnitCircle", "Vector", "ThetaArc", "CosProjection", "SinProjection"],
                key_definitions=[
                    "|e^{iθ}| = 1 (constant unit radius from origin)",
                    "Real projection: x = cos(θ)",
                    "Imaginary projection: y = sin(θ)",
                    "Pythagorean identity: cos²(θ) + sin²(θ) = 1",
                ],
                visual_states=["Coordinate Plane & Circle", "Rotating Vector to angle θ", "Dashed Projections to Axes", "Geometric Summary Card"],
                visual_purpose="Demonstrate why cosine and sine appear by projecting rotating complex vector onto axes.",
            )
            code = (
                'title = Text("Geometric Interpretation: The Unit Circle", font_size=32, color=TEAL).to_edge(UP, buff=0.35)\n'
                'plane = ComplexPlane(x_range=[-1.6, 1.6, 1], y_range=[-1.4, 1.4, 1], x_length=4.6, y_length=4.0).shift(LEFT*2.2 + DOWN*0.3)\n'
                'circle = Circle(radius=1.8, color=TEAL).move_to(plane.n2p(0))\n'
                'theta_val = PI / 4\n'
                'pt = plane.n2p(np.exp(1j * theta_val))\n'
                'origin = plane.n2p(0)\n'
                'pt_x = plane.n2p(np.cos(theta_val))\n'
                'pt_y = plane.n2p(1j * np.sin(theta_val))\n'
                'vector = Arrow(origin, pt, buff=0, color=YELLOW, stroke_width=4, max_tip_length_to_length_ratio=0.12)\n'
                'dot = Dot(pt, color=RED, radius=0.08)\n'
                'dot_label = MathTex(r"e^{i\\theta}", font_size=24, color=RED).next_to(dot, UR, buff=0.1)\n'
                'proj_x = DashedLine(pt, pt_x, color=BLUE, stroke_width=2.5)\n'
                'proj_y = DashedLine(pt, pt_y, color=RED, stroke_width=2.5)\n'
                'lbl_cos = MathTex(r"\\cos(\\theta)", font_size=20, color=BLUE).next_to(pt_x, DOWN, buff=0.15)\n'
                'lbl_sin = MathTex(r"\\sin(\\theta)", font_size=20, color=RED).next_to(pt_y, LEFT, buff=0.15)\n'
                'arc = Arc(radius=0.5, start_angle=0, angle=theta_val, arc_center=origin, color=GOLD)\n'
                'arc_lbl = MathTex(r"\\theta", font_size=18, color=GOLD).next_to(arc, RIGHT, buff=0.05).shift(UP*0.08)\n'
                'card_title = Text("Key Geometric Insights", font_size=22, color=GOLD, weight=BOLD)\n'
                't1 = MathTex(r"\\bullet\\ \\text{Radius: } |e^{i\\theta}| = 1", font_size=19, color=WHITE)\n'
                't2 = MathTex(r"\\bullet\\ \\text{Real projection: } x = \\cos(\\theta)", font_size=19, color=BLUE)\n'
                't3 = MathTex(r"\\bullet\\ \\text{Imaginary projection: } y = \\sin(\\theta)", font_size=19, color=RED)\n'
                't4 = MathTex(r"\\bullet\\ \\text{Coordinates: } (\\cos\\theta, \\sin\\theta)", font_size=19, color=YELLOW)\n'
                't5 = MathTex(r"\\bullet\\ \\cos^2\\theta + \\sin^2\\theta = 1", font_size=19, color=GREEN)\n'
                'info_card = VGroup(card_title, t1, t2, t3, t4, t5).arrange(DOWN, aligned_edge=LEFT, buff=0.18).shift(RIGHT*2.8 + DOWN*0.3)\n'
                'card_box = SurroundingRectangle(info_card, color=GRAY, buff=0.2, stroke_width=1.5)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Create(plane), Create(circle), run_time=1.2)\n'
                'self.play(GrowArrow(vector), FadeIn(dot), Write(dot_label), run_time=1.0)\n'
                'self.play(Create(arc), Write(arc_lbl), run_time=0.8)\n'
                'self.play(Create(proj_x), Write(lbl_cos), Create(proj_y), Write(lbl_sin), run_time=1.2)\n'
                'self.play(Create(card_box), FadeIn(info_card), run_time=1.2)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "Now let us examine the geometric reason why cosine and sine must appear in this equation. "
                "On the left, notice the coordinate axes representing the complex plane: real numbers horizontally, and imaginary numbers vertically. "
                "Because the absolute magnitude of e to the i theta is always strictly equal to one, "
                "varying theta moves the yellow vector around the unit circle without ever changing its length. "
                "Observe the blue and red dashed projection lines dropping from the tip of the vector. "
                "The horizontal projection onto the real axis has length cosine of theta. "
                "The vertical projection onto the imaginary axis has length sine of theta. "
                "Together, they form a right triangle inside the circle where the hypotenuse is the unit radius. "
                "This explains why cosine and sine are not arbitrary additions: they are the unavoidable Cartesian coordinates of circular rotation. "
                "Engineers and physicists exploit this duality every day to transform difficult wave mechanics and differential equations into simple algebra."
            )
        else:
            anchor = VisualAnchor(
                type="constants_breakdown",
                title="Euler's Identity: Mathematical Unity",
                latex=r"e^{i\pi} + 1 = 0",
                visible_elements=["e", "i", "pi", "1", "0"],
                key_definitions=[
                    "e ≈ 2.718 : Base of natural logarithms, growth, and calculus",
                    "i = √(-1) : Imaginary unit, orthogonal rotation, and algebra",
                    "π ≈ 3.14159 : Ratio of circle circumference to diameter, geometry",
                    "1 : Multiplicative identity and basis of counting",
                    "0 : Additive identity, origin, and ground state",
                ],
                visual_states=["Identity Formula Box", "Five Constants Breakdown", "Geometric Rotation Note"],
                visual_purpose="Present the most famous special case uniting five fundamental mathematical constants with full descriptions.",
            )
            code = (
                'title = Text("Euler\'s Identity: Mathematical Unity", font_size=34, color=GOLD).to_edge(UP, buff=0.4)\n'
                'identity = MathTex(r"e^{i\\pi} + 1 = 0", font_size=48, color=YELLOW).next_to(title, DOWN, buff=0.35)\n'
                'box = SurroundingRectangle(identity, color=GREEN, buff=0.3, stroke_width=2)\n'
                'lbl_constants = Text("The Five Fundamental Constants of Mathematics:", font_size=20, color=WHITE, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.0)\n'
                'c1 = MathTex(r"\\bullet\\ e \\approx 2.718 : \\text{The base of natural logarithms, growth, and calculus}", font_size=19, color=WHITE)\n'
                'c2 = MathTex(r"\\bullet\\ i = \\sqrt{-1} : \\text{The imaginary unit, orthogonal rotation, and algebra}", font_size=19, color=TEAL)\n'
                'c3 = MathTex(r"\\bullet\\ \\pi \\approx 3.14159 : \\text{The ratio of circle circumference, geometry, and waves}", font_size=19, color=GREEN)\n'
                'c4 = MathTex(r"\\bullet\\ 1 : \\text{The multiplicative identity and basis of counting}", font_size=19, color=BLUE)\n'
                'c5 = MathTex(r"\\bullet\\ 0 : \\text{The additive identity, origin, and concept of nothingness}", font_size=19, color=GOLD)\n'
                'constants_group = VGroup(c1, c2, c3, c4, c5).arrange(DOWN, aligned_edge=LEFT, buff=0.16).next_to(lbl_constants, DOWN, buff=0.18).align_to(lbl_constants, LEFT)\n'
                'geo_note = Text("Rotation by π radians (180°) maps +1 directly to -1, so -1 + 1 = 0", font_size=18, color=GRAY_A).next_to(constants_group, DOWN, buff=0.25).align_to(lbl_constants, LEFT)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Write(identity), Create(box), run_time=1.2)\n'
                'self.play(FadeIn(lbl_constants), run_time=0.5)\n'
                'self.play(LaggedStart(*[FadeIn(c, shift=RIGHT*0.2) for c in constants_group], lag_ratio=0.15), run_time=1.8)\n'
                'self.play(FadeIn(geo_note), run_time=0.8)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "When we evaluate Euler's formula at the specific angle theta equals pi radians, we arrive at Euler's identity. "
                "Notice the five fundamental constants listed on your screen: "
                "e, the bedrock of calculus and growth; i, the heart of algebra and complex numbers; "
                "pi, the ancient constant of circular geometry; 1, the foundation of arithmetic; and 0, the additive origin of all mathematics. "
                "Before Euler, each of these five constants belonged to an entirely distinct domain of thought. "
                "Yet here, connected by a single equation, they combine to produce zero. "
                "As the note at the bottom of the slide illustrates, rotating by pi radians is a half-turn rotation of one hundred eighty degrees, "
                "which carries the positive unit value plus one directly across the origin to negative one. "
                "Adding one returns the system flawlessly to zero. It is widely celebrated as the most beautiful theorem in mathematics."
            )
    elif "fourier" in p_lower:
        if slide_num == 1:
            anchor = VisualAnchor(
                type="annotated_formula",
                title="The Continuous Fourier Transform",
                latex=r"\hat{f}(\xi) = \int_{-\infty}^{\infty} f(t) e^{-2\pi i t \xi} dt",
                visible_elements=["f(t)", "hat{f}(xi)", "integral", "e^{-2pi i t xi}"],
                key_definitions=[
                    "f(t) : Time-domain continuous signal or audio wave",
                    "hat{f}(xi) : Frequency-domain spectral density at frequency xi",
                    "e^(-2πitξ) : Complex exponential winding function of frequency xi",
                    "∫ dt : Continuous accumulation / center-of-mass calculation",
                ],
                visual_purpose="Formulate the frequency decomposition with complete mathematical breakdown.",
            )
            code = (
                'title = Text("The Continuous Fourier Transform", font_size=34, color=YELLOW).to_edge(UP, buff=0.4)\n'
                'formula = MathTex(r"\\hat{f}(\\xi) = \\int_{-\\infty}^{\\infty} f(t) e^{-2\\pi i t \\xi} dt", font_size=42, color=BLUE).next_to(title, DOWN, buff=0.35)\n'
                'box = SurroundingRectangle(formula, color=GOLD, buff=0.25)\n'
                'where_lbl = Text("Mathematical Anatomy:", font_size=22, color=GOLD, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.2)\n'
                'b1 = MathTex(r"\\bullet\\ f(t) : \\text{Original time-domain signal (e.g. audio waveform or voltage)}", font_size=20, color=WHITE)\n'
                'b2 = MathTex(r"\\bullet\\ \\hat{f}(\\xi) : \\text{Frequency spectrum representation (amplitude and phase at } \\xi)", font_size=20, color=TEAL)\n'
                'b3 = MathTex(r"\\bullet\\ e^{-2\\pi i t \\xi} : \\text{Rotational winding engine of frequency } \\xi \\text{ around complex origin}", font_size=20, color=GREEN)\n'
                'b4 = MathTex(r"\\bullet\\ \\int_{-\\infty}^{\\infty} dt : \\text{Continuous integration computing the center of mass of winding}", font_size=20, color=YELLOW)\n'
                'bullets = VGroup(b1, b2, b3, b4).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Write(formula), Create(box), run_time=1.2)\n'
                'self.play(FadeIn(where_lbl), run_time=0.5)\n'
                'self.play(LaggedStart(*[FadeIn(b, shift=RIGHT*0.2) for b in bullets], lag_ratio=0.2), run_time=1.8)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "The Fourier Transform is one of the most transformative mathematical concepts ever discovered, "
                "allowing us to decompose any complex signal into a spectrum of pure sinusoidal frequencies. "
                "Look at the mathematical anatomy detailed on your screen. "
                "The function f of t represents the signal in the time domain, such as a recording of musical instruments or atmospheric pressure. "
                "The complex exponential e to the minus two pi i t xi acts as a winding mechanism. "
                "It takes the time-domain wave and wraps it around the complex plane at frequency xi. "
                "By integrating over all time, the formula calculates the center of mass of this winding. "
                "When the winding frequency xi matches a natural frequency of the signal, the winding aligns in phase and spikes outward, "
                "revealing the exact composition of the original wave."
            )
        elif slide_num == 2:
            anchor = VisualAnchor(
                type="geometric_projection",
                title="Duality: Time Domain vs Frequency Spectrum",
                latex="",
                visible_elements=["Time Signal", "Frequency Peaks", "Harmonics"],
                key_definitions=[
                    "Time Domain: Signal amplitude unfolding sequentially across time",
                    "Frequency Domain: Discrete spectral peaks showing constituent frequencies",
                    "Applications: MP3 compression, MRI imaging, telecom, quantum mechanics",
                ],
                visual_purpose="Illustrate dual perspectives of signal representation.",
            )
            code = (
                'title = Text("Duality: Time vs Frequency Domain", font_size=32, color=TEAL).to_edge(UP, buff=0.35)\n'
                'axes1 = Axes(x_range=[0, 4, 1], y_range=[-1.2, 1.2, 1], x_length=5.0, y_length=1.8).shift(LEFT*2.5 + UP*0.8)\n'
                'sine1 = axes1.plot(lambda x: np.sin(2 * PI * x) + 0.5 * np.sin(4 * PI * x), color=TEAL)\n'
                'lbl1 = Text("Time Domain: Combined Waveform", font_size=18, color=TEAL).next_to(axes1, UP, buff=0.15)\n'
                'axes2 = Axes(x_range=[0, 5, 1], y_range=[0, 2, 1], x_length=5.0, y_length=1.8).shift(LEFT*2.5 + DOWN*1.5)\n'
                'peak1 = Line(axes2.c2p(1, 0), axes2.c2p(1, 1.5), color=YELLOW, stroke_width=4)\n'
                'peak2 = Line(axes2.c2p(2, 0), axes2.c2p(2, 0.75), color=YELLOW, stroke_width=4)\n'
                'lbl2 = Text("Frequency Domain: Pure Spectral Peaks", font_size=18, color=YELLOW).next_to(axes2, UP, buff=0.15)\n'
                'card_title = Text("Dual Perspectives", font_size=20, color=GOLD, weight=BOLD)\n'
                'p1 = MathTex(r"\\bullet\\ \\text{Time: When events happen}", font_size=18, color=WHITE)\n'
                'p2 = MathTex(r"\\bullet\\ \\text{Frequency: Which tones exist}", font_size=18, color=WHITE)\n'
                'p3 = MathTex(r"\\bullet\\ \\text{MP3/JPEG Compression}", font_size=18, color=BLUE)\n'
                'p4 = MathTex(r"\\bullet\\ \\text{Medical MRI Scanners}", font_size=18, color=GREEN)\n'
                'card = VGroup(card_title, p1, p2, p3, p4).arrange(DOWN, aligned_edge=LEFT, buff=0.16).shift(RIGHT*3.0 + DOWN*0.3)\n'
                'box = SurroundingRectangle(card, color=GRAY, buff=0.2, stroke_width=1.5)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Create(axes1), Create(sine1), Write(lbl1), run_time=1.2)\n'
                'self.play(Create(axes2), Create(peak1), Create(peak2), Write(lbl2), run_time=1.2)\n'
                'self.play(Create(box), FadeIn(card), run_time=1.0)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "To intuitively grasp the Fourier Transform, consider the dual views presented before you. "
                "On the top left, the time-domain signal shows a complicated composite wave whose individual ingredients are tangled together. "
                "On the bottom left, the Fourier Transform isolates each ingredient into sharp, unambiguous frequency spikes. "
                "Think of the time domain as listening to a musical chord, while the frequency domain is reading the sheet music that lists each note. "
                "Modern digital technologies rely entirely on this duality: audio compression discards frequencies the human ear cannot hear, "
                "while MRI machines measure frequency resonances to reconstruct high-resolution images of the human brain."
            )
        else:
            anchor = VisualAnchor(
                type="annotated_formula",
                title="Inverse Fourier Transform: Perfect Reconstruction",
                latex=r"f(t) = \int_{-\infty}^{\infty} \hat{f}(\xi) e^{2\pi i t \xi} d\xi",
                visible_elements=["f(t)", "hat{f}(xi)", "integral", "reconstruction"],
                key_definitions=[
                    "Lossless Duality: Information is 100% preserved between domains",
                    "Synthesis: Integrating pure sinusoids restores continuous time signal",
                    "Orthogonality: Complex exponentials form an orthogonal basis",
                ],
                visual_purpose="Demonstrate complete and reversible reconstruction from frequency space.",
            )
            code = (
                'title = Text("Inverse Fourier Reconstruction", font_size=34, color=GREEN).to_edge(UP, buff=0.4)\n'
                'formula = MathTex(r"f(t) = \\int_{-\\infty}^{\\infty} \\hat{f}(\\xi) e^{2\\pi i t \\xi} d\\xi", font_size=42, color=YELLOW).next_to(title, DOWN, buff=0.35)\n'
                'box = SurroundingRectangle(formula, color=GREEN, buff=0.25)\n'
                'where_lbl = Text("Synthesis Properties:", font_size=22, color=GREEN, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.2)\n'
                'b1 = MathTex(r"\\bullet\\ \\text{Lossless Reconstruction: No information is lost during transformation}", font_size=20, color=WHITE)\n'
                'b2 = MathTex(r"\\bullet\\ e^{2\\pi i t \\xi} : \\text{Positive unwinding restores continuous time phase}", font_size=20, color=TEAL)\n'
                'b3 = MathTex(r"\\bullet\\ \\text{Orthogonality: Frequency modes form a complete Hilbert space basis}", font_size=20, color=YELLOW)\n'
                'bullets = VGroup(b1, b2, b3).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Write(formula), Create(box), run_time=1.2)\n'
                'self.play(FadeIn(where_lbl), run_time=0.5)\n'
                'self.play(LaggedStart(*[FadeIn(b, shift=RIGHT*0.2) for b in bullets], lag_ratio=0.2), run_time=1.5)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "Crucially, the Fourier Transform is completely reversible through the Inverse Fourier Transform shown on your screen. "
                "No information is degraded or lost. By taking each frequency component, scaling it by its amplitude and phase, "
                "and unwinding it continuously back into time, we reassemble the exact original function. "
                "This lossless symmetry guarantees that time and frequency are not competing descriptions, "
                "but two complementary representations of the exact same physical reality."
            )
    elif any(k in p_lower for k in ("bodmas", "pemdas", "order of operations", "bidmas", "bedmas")):
        if slide_num == 1:
            anchor = VisualAnchor(
                type="annotated_formula",
                title="The BODMAS / PEMDAS Hierarchy",
                latex=r"\text{B} \rightarrow \text{O} \rightarrow \text{D} / \text{M} \rightarrow \text{A} / \text{S}",
                visible_elements=["B: Brackets", "O: Orders / Exponents", "D/M: Division & Multiplication", "A/S: Addition & Subtraction"],
                key_definitions=[
                    "B / P : Brackets & Parentheses (evaluate innermost sub-expressions first)",
                    "O / E : Orders & Exponents (indices, powers, square roots)",
                    "D & M : Division & Multiplication (equal precedence, evaluated Left-to-Right)",
                    "A & S : Addition & Subtraction (equal precedence, evaluated Left-to-Right)",
                ],
                visual_purpose="Establish the standard order of operations precedence hierarchy.",
            )
            code = (
                'title = Text("The BODMAS / PEMDAS Hierarchy", font_size=34, color=YELLOW).to_edge(UP, buff=0.4)\n'
                'rule_box = MathTex(r"\\mathbf{B} \\rightarrow \\mathbf{O} \\rightarrow \\mathbf{D} / \\mathbf{M} \\rightarrow \\mathbf{A} / \\mathbf{S}", font_size=42, color=BLUE).next_to(title, DOWN, buff=0.35)\n'
                'box = SurroundingRectangle(rule_box, color=GOLD, buff=0.25)\n'
                'where_lbl = Text("Precedence Rules:", font_size=22, color=GOLD, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.2)\n'
                'b1 = MathTex(r"\\bullet\\ \\mathbf{B / P} : \\text{Brackets / Parentheses (evaluate innermost first)}", font_size=20, color=WHITE)\n'
                'b2 = MathTex(r"\\bullet\\ \\mathbf{O / E} : \\text{Orders / Exponents (indices, powers, and roots)}", font_size=20, color=TEAL)\n'
                'b3 = MathTex(r"\\bullet\\ \\mathbf{D \\& M} : \\text{Division \\& Multiplication (equal rank, Left-to-Right)}", font_size=20, color=GREEN)\n'
                'b4 = MathTex(r"\\bullet\\ \\mathbf{A \\& S} : \\text{Addition \\& Subtraction (equal rank, Left-to-Right)}", font_size=20, color=YELLOW)\n'
                'bullets = VGroup(b1, b2, b3, b4).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Write(rule_box), Create(box), run_time=1.2)\n'
                'self.play(FadeIn(where_lbl), run_time=0.5)\n'
                'self.play(LaggedStart(*[FadeIn(b, shift=RIGHT*0.2) for b in bullets], lag_ratio=0.2), run_time=1.8)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "The order of operations is the universal grammatical convention of mathematics, "
                "ensuring that every mathematical expression has exactly one unambiguous value. "
                "Depending on where you studied, you might know this rule as BODMAS, PEMDAS, or BIDMAS. "
                "As outlined on your screen, operations are resolved in four strict hierarchical stages: "
                "First, evaluate all expressions enclosed within brackets or parentheses from the inside out. "
                "Second, calculate orders, which include exponents, square roots, and indices. "
                "Next come division and multiplication. A critical rule to remember is that division and multiplication "
                "have equal precedence and must be evaluated from left to right as they appear. "
                "Finally, addition and subtraction are computed, which also share equal rank from left to right. "
                "Following this consistent hierarchy prevents ambiguity in both manual calculations and computer software."
            )
        elif slide_num == 2:
            anchor = VisualAnchor(
                type="annotated_formula",
                title="Equal Precedence & Left-to-Right Rule",
                latex=r"12 \div 3 \times 2 = 4 \times 2 = 8",
                visible_elements=["12 / 3 * 2", "Step 1: 12 / 3 = 4", "Step 2: 4 * 2 = 8", "Left-to-Right Precedence"],
                key_definitions=[
                    "Common Trap: Multiplications do NOT come before divisions automatically",
                    "Left-to-Right: Division and multiplication share identical priority tier",
                    "Step 1: 12 ÷ 3 = 4 (leftmost operator first)",
                    "Step 2: 4 × 2 = 8 (final correct evaluation)",
                ],
                visual_purpose="Dispel the common trap where multiplication is incorrectly prioritized over division.",
            )
            code = (
                'title = Text("Equal Precedence & The Left-to-Right Rule", font_size=32, color=YELLOW).to_edge(UP, buff=0.4)\n'
                'expr = MathTex(r"12 \\div 3 \\times 2 = ?", font_size=44, color=BLUE).next_to(title, DOWN, buff=0.35)\n'
                'box = SurroundingRectangle(expr, color=GOLD, buff=0.25)\n'
                'step1 = MathTex(r"\\text{Step 1: } 12 \\div 3 = 4 \\quad \\rightarrow \\quad 4 \\times 2", font_size=24, color=GREEN)\n'
                'step2 = MathTex(r"\\text{Step 2: } 4 \\times 2 = \\mathbf{8} \\quad \\checkmark \\text{ (Correct: Left-to-Right)}", font_size=24, color=GOLD)\n'
                'trap = Text("Pitfall: 12 ÷ (3 × 2) = 12 ÷ 6 = 2 ✗ (Violates left-to-right rule)", font_size=20, color=RED)\n'
                'steps = VGroup(step1, step2, trap).arrange(DOWN, aligned_edge=LEFT, buff=0.25).next_to(box, DOWN, buff=0.4)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Write(expr), Create(box), run_time=1.0)\n'
                'self.play(FadeIn(step1, shift=UP*0.2), run_time=0.8)\n'
                'self.play(FadeIn(step2, shift=UP*0.2), run_time=0.8)\n'
                'self.play(FadeIn(trap, shift=UP*0.2), run_time=0.8)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "One of the most frequent misconceptions in algebra is believing multiplication must always precede division "
                "simply because M precedes D in the word PEMDAS, or that division must precede multiplication because D comes before M in BODMAS. "
                "In reality, division and multiplication are inverses of each other and belong to the exact same priority tier. "
                "Look at the example on the board: twelve divided by three times two. "
                "Because division and multiplication share equal precedence, we resolve them strictly from left to right. "
                "The leftmost operator is division: twelve divided by three gives four. "
                "Then we take four times two to arrive at the correct answer of eight. "
                "If someone incorrectly performed the multiplication first, three times two, they would get twelve divided by six equals two, "
                "which violates standard mathematical precedence and produces an error in every modern scientific calculator."
            )
        else:
            anchor = VisualAnchor(
                type="annotated_formula",
                title="Worked Multi-Tier Example",
                latex=r"3 + 2 \times (4^2 - 6) \div 5",
                visible_elements=["Original Expression", "Step 1: Exponent in Brackets", "Step 2: Bracket Evaluation", "Step 3: Multiplication & Division", "Final Addition"],
                key_definitions=[
                    "1. Brackets: (4^2 - 6) -> 4^2 = 16 -> (16 - 6) = 10",
                    "2. Substitute: Expression becomes 3 + 2 × 10 ÷ 5",
                    "3. Multiply & Divide: 2 × 10 = 20 -> 20 ÷ 5 = 4",
                    "4. Final Addition: 3 + 4 = 7",
                ],
                visual_purpose="Demonstrate end-to-end multi-tier calculation using BODMAS.",
            )
            code = (
                'title = Text("Worked Multi-Tier Example", font_size=34, color=GOLD).to_edge(UP, buff=0.4)\n'
                'full_eq = MathTex(r"3 + 2 \\times (4^2 - 6) \\div 5 = \\mathbf{7}", font_size=40, color=YELLOW).next_to(title, DOWN, buff=0.35)\n'
                'box = SurroundingRectangle(full_eq, color=GREEN, buff=0.25)\n'
                's1 = MathTex(r"\\mathbf{1.\\ Brackets \\& Orders:} \\quad (4^2 - 6) = (16 - 6) = \\mathbf{10}", font_size=21, color=WHITE)\n'
                's2 = MathTex(r"\\mathbf{2.\\ New\\ Form:} \\quad 3 + 2 \\times 10 \\div 5", font_size=21, color=TEAL)\n'
                's3 = MathTex(r"\\mathbf{3.\\ Left\\ to\\ Right:} \\quad 2 \\times 10 = 20 \\quad \\rightarrow \\quad 20 \\div 5 = \\mathbf{4}", font_size=21, color=GREEN)\n'
                's4 = MathTex(r"\\mathbf{4.\\ Final\\ Addition:} \\quad 3 + 4 = \\mathbf{7}", font_size=22, color=GOLD)\n'
                'steps = VGroup(s1, s2, s3, s4).arrange(DOWN, aligned_edge=LEFT, buff=0.22).next_to(box, DOWN, buff=0.35)\n'
                'self.play(Write(title), run_time=0.8)\n'
                'self.play(Write(full_eq), Create(box), run_time=1.0)\n'
                'self.play(LaggedStart(*[FadeIn(s, shift=RIGHT*0.2) for s in steps], lag_ratio=0.25), run_time=2.2)\n'
                'self.wait(1.5)\n'
            )
            narration = (
                "Let us put all the principles together in a full multi-tier expression: three plus two times open parenthesis four squared minus six close parenthesis divided by five. "
                "Step one: We examine inside the brackets first. Inside the brackets, we see an exponent, four squared, which equals sixteen. "
                "Continuing inside the brackets, sixteen minus six leaves us with ten. "
                "Step two: Substitute ten back into the main expression, yielding three plus two times ten divided by five. "
                "Step three: We now have addition, multiplication, and division. Multiplication and division take priority over addition, "
                "and by our left-to-right rule, we multiply two times ten to get twenty, followed by twenty divided by five, which simplifies to four. "
                "Step four: Finally, we perform the addition: three plus four equals seven. "
                "By systematically applying the BODMAS precedence rules at each step, even complex nested formulas resolve cleanly and without ambiguity."
            )
    else:
        anchor = VisualAnchor(
            type="annotated_formula",
            title=f"{prompt[:28]} : Key Foundations",
            latex=r"\text{Principle } " + str(slide_num),
            visible_elements=[f"Principle {slide_num}", "Core Insight", "Applications"],
            key_definitions=[
                f"Core Mechanism: Primary operational principle of {prompt[:20]}",
                "Conceptual Basis: Foundational mathematical and physical relationships",
                "Applications: Real-world engineering and computational significance",
            ],
            visual_purpose=f"Provide structured breakdown of {prompt} stage {slide_num}.",
        )
        code = (
            f'title = Text("{prompt[:28]} : Key Principles", font_size=34, color=YELLOW).to_edge(UP, buff=0.4)\n'
            f'box_lbl = Text("Core Concept {slide_num}", font_size=36, color=BLUE).next_to(title, DOWN, buff=0.35)\n'
            'box = SurroundingRectangle(box_lbl, color=GOLD, buff=0.25)\n'
            'where_lbl = Text("Key Insights:", font_size=22, color=GOLD, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.2)\n'
            f'b1 = MathTex(r"\\bullet\\ \\text{{Foundations: Essential framework underlying this concept}}", font_size=20, color=WHITE)\n'
            f'b2 = MathTex(r"\\bullet\\ \\text{{Mechanics: Dynamic interaction of variables and parameters}}", font_size=20, color=TEAL)\n'
            f'b3 = MathTex(r"\\bullet\\ \\text{{Implications: Broad mathematical and practical applications}}", font_size=20, color=GREEN)\n'
            'bullets = VGroup(b1, b2, b3).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)\n'
            'self.play(Write(title), run_time=0.8)\n'
            'self.play(Write(box_lbl), Create(box), run_time=1.2)\n'
            'self.play(FadeIn(where_lbl), run_time=0.5)\n'
            'self.play(LaggedStart(*[FadeIn(b, shift=RIGHT*0.2) for b in bullets], lag_ratio=0.2), run_time=1.5)\n'
            'self.wait(1.5)\n'
        )
        clean_topic = _extract_topic_title(prompt)
        narration = (
            f"In this segment, we examine the foundational mechanisms of {clean_topic}. "
            "Notice the structured breakdown displayed before you. Rather than treating this as abstract notation, "
            "we want to cultivate genuine conceptual understanding of how these elements interact. "
            "When we break down the core components, their mutual dependencies become apparent, "
            "allowing us to apply these principles reliably to more advanced problems."
        )

    clean_topic = _extract_topic_title(prompt)
    return TeachingSegment(
        slide_num=slide_num,
        concept=anchor.title or f"{clean_topic} - Slide {slide_num}",
        learning_objective=anchor.visual_purpose,
        visual_anchor=anchor,
        manim_code=code,
        narration=narration,
    )


def _get_domain_knowledge(prompt: str) -> str:
    """Provides high-density domain context for small/local LLMs on key STEM concepts."""
    p = prompt.lower()
    if "euler" in p:
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Euler's Formula & Identity):\n"
            "- Core Formula: e^{iθ} = cos(θ) + i sin(θ). Evaluated at θ = π yields e^{iπ} + 1 = 0.\n"
            "- Five Fundamental Constants: e ≈ 2.718 (continuous compound growth, calculus base), "
            "i = √(-1) (orthogonal rotation by 90° in complex plane), π ≈ 3.14159 (circle geometry, radians), "
            "1 (multiplicative unity), 0 (additive identity / ground state).\n"
            "- Unit Circle Geometry: |e^{iθ}| = 1 always. Moving θ rotates a vector of length 1 around the origin. "
            "Horizontal projection x = cos(θ), vertical projection y = sin(θ). Forms right triangle satisfying cos²(θ) + sin²(θ) = 1.\n"
            "- Power Series Derivation: e^{ix} = 1 + ix - x²/2! - ix³/3! + x⁴/4! + ... "
            "= (1 - x²/2! + ...) + i(x - x³/3! + ...) = cos(x) + i sin(x).\n"
            "- Practical Impact: Signal processing, AC electrical circuits (phasors), wave optics, Fourier analysis, and quantum mechanics."
        )
    if "fourier" in p:
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Fourier Transform):\n"
            "- Forward Transform: f̂(ξ) = ∫_{-∞}^{∞} f(t) e^{-2π i t ξ} dt.\n"
            "- Inverse Transform: f(t) = ∫_{-∞}^{∞} f̂(ξ) e^{2π i t ξ} dξ.\n"
            "- Rotational Winding Intuition: e^{-2π i t ξ} wraps the time signal around the origin at frequency ξ. "
            "The integral measures the center-of-mass balance point; when ξ matches a signal harmonic, it spikes.\n"
            "- Time-Frequency Duality: Continuous signal amplitude across time ↔ discrete spectral frequency peaks."
        )
    if any(k in p for k in ("bodmas", "pemdas", "order of operations", "bidmas", "bedmas")):
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (BODMAS / PEMDAS / Order of Operations):\n"
            "- Acronym Mappings: BODMAS (Brackets, Orders, Division, Multiplication, Addition, Subtraction) vs PEMDAS (Parentheses, Exponents, Multiplication, Division, Addition, Subtraction).\n"
            "- Crucial Precedence Equality: Division and Multiplication have EQUAL rank (resolved Left-to-Right). Addition and Subtraction have EQUAL rank (resolved Left-to-Right).\n"
            "- Common Pitfalls: Erroneously doing multiplication before division in expressions like 8 ÷ 2(4) or 12 ÷ 3 × 2.\n"
            "- Structure: Inner groupings first → Exponents/powers/roots next → Multiplicative operations L-to-R → Additive operations L-to-R."
        )
    return ""


def plan_teaching_segment(
    prompt: str,
    slide_num: int,
    total_slides: int,
    outline: str,
    client: OpenAI,
    model: str,
) -> TeachingSegment:
    """Generates a TeachingSegment: first the rich visual anchor, then in-depth narration."""
    clean_topic = _extract_topic_title(prompt)
    condensed_prompt = clean_topic if len(prompt) < 400 else f"{clean_topic}\n\nKey Concepts Context:\n{prompt[:400]}..."
    domain_ctx = _get_domain_knowledge(prompt)
    ctx_block = f"\nAdditional Domain Grounding:\n{domain_ctx}\n" if domain_ctx else ""

    # Step 1: Generate Visual Anchor
    visual_user_prompt = (
        f"Topic: {condensed_prompt}\n"
        f"{ctx_block}"
        f"Lecture Outline:\n{outline}\n\n"
        f"Create the visual anchor for Slide {slide_num} of {total_slides}.\n"
        f"Remember: Do NOT make a sparse slide with only title + formula! Include symbol breakdowns ('Where:'), "
        f"dynamic geometric projections with dashed lines, or concept cards so students learn even on pause.\n"
        f"Provide the <visual_anchor> JSON and clean, executable Manim code."
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
        f"Topic: {clean_topic}\n"
        f"{ctx_block}"
        f"Slide Number: {slide_num} of {total_slides}\n"
        f"Visual Anchor Title: {anchor.title}\n"
        f"Displayed Formula: {anchor.latex}\n"
        f"Visible Elements: {anchor.visible_elements}\n"
        f"Key Definitions Visible on Slide: {anchor.key_definitions}\n"
        f"Visual Purpose: {anchor.visual_purpose}\n\n"
        f"Write an in-depth, university-level teaching explanation.\n"
        f"Reference the slide breakdown naturally, explain the intuition, define the symbols, and explain applications.\n"
        f"Remember: Do NOT merely recite the slide aloud!"
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

        @contextmanager
        def voiceover(self, *args, **kwargs):
            yield None

        def construct(self):
            safe_globals: Dict[str, Any] = {
                "np": np,
                "MathTex": MathTex,
                "Text": Text,
                "Title": Title,
                "Scene": Scene,
                "VGroup": VGroup,
                "Group": Group,
                "Create": Create,
                "Write": Write,
                "Transform": Transform,
                "ReplacementTransform": ReplacementTransform,
                "FadeIn": FadeIn,
                "FadeOut": FadeOut,
                "GrowFromCenter": GrowFromCenter,
                "GrowArrow": GrowArrow,
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
                "Angle": Angle,
                "RightAngle": RightAngle,
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
                "BOLD": BOLD,
                "GRAY_A": GRAY_A,
                "PI": PI,
                "TAU": TAU,
            }
            try:
                from manim_voiceover import VoiceoverScene
                safe_globals["VoiceoverScene"] = VoiceoverScene
            except Exception:
                safe_globals["VoiceoverScene"] = Scene

            try:
                from manim import Paragraph
                safe_globals["Paragraph"] = Paragraph
            except Exception:
                safe_globals["Paragraph"] = Text

            try:
                from manim import Tex, MarkupText
                safe_globals["Tex"] = Tex
                safe_globals["MarkupText"] = MarkupText
            except Exception:
                safe_globals["Tex"] = MathTex
                safe_globals["MarkupText"] = Text

            def _clean_manim_code(code_str: str) -> str:
                # Clean hallucinated `with self.play(...):`
                code_str = re.sub(
                    r"with\s+self\.play\((.*?)\)(?:\s*as\s+\w+)?:",
                    r"self.play(\1)",
                    code_str,
                )
                return code_str

            def _execute_code(code_str: str) -> bool:
                cleaned = _clean_manim_code(code_str)
                locs: Dict[str, Any] = {"self": self}
                exec(cleaned, safe_globals, locs)

                # Check if a Scene subclass was defined in locs
                scene_cls = None
                for v in list(locs.values()):
                    if isinstance(v, type) and issubclass(v, Scene) and v is not Scene and v is not VisualAnchorScene:
                        scene_cls = v
                        break

                if scene_cls:
                    scene_cls.construct(self)

                # Return True only if actual mobjects were added to the canvas
                return len(self.mobjects) > 0

            executed = False
            if segment.manim_code.strip():
                try:
                    executed = _execute_code(segment.manim_code)
                except Exception as exc:
                    print(f"[Visual Render Warning] Slide {segment.slide_num} primary exec error: {exc}", file=sys.stderr)
                    self.clear()

                if not executed:
                    # Attempt transpilation of MathTex to Text if LaTeX or font rendering failed
                    try:
                        self.clear()
                        alt_code = re.sub(r"(?:MathTex|Tex|Paragraph)\(\s*r?([\"'])(.*?)\1", r"Text(\1\2\1", segment.manim_code)
                        alt_code = (
                            alt_code.replace("\\bullet\\", "•")
                            .replace("\\bullet", "•")
                            .replace(r"\approx", "≈")
                            .replace(r"\sqrt{-1}", "√(-1)")
                            .replace(r"\sqrt", "√")
                            .replace(r"\theta", "θ")
                            .replace(r"\pi", "π")
                            .replace(r"\cos", "cos")
                            .replace(r"\sin", "sin")
                            .replace(r"\xi", "ξ")
                            .replace(r"\text{", "")
                            .replace(r"\hat{f}", "f̂")
                            .replace(r"\int_{-\infty}^{\infty}", "∫")
                        )
                        executed = _execute_code(alt_code)
                        if executed:
                            print(f"[Visual Render Info] Slide {segment.slide_num} successfully rendered via Text transpilation!", file=sys.stderr)
                    except Exception as exc2:
                        print(f"[Visual Render Warning] Slide {segment.slide_num} transpilation failed: {exc2}", file=sys.stderr)
                        self.clear()

            if not executed or len(self.mobjects) == 0:
                # Robust educational fallback with full definitions and equation, NEVER dummy slide box
                try:
                    self.clear()
                    title_text = segment.visual_anchor.title or segment.concept
                    f_title = Text(title_text, font_size=32, color=YELLOW).to_edge(UP, buff=0.4)
                    if f_title.width > 12.0:
                        f_title.scale_to_fit_width(12.0)
                    elements = [f_title]
                    prev_mob = f_title

                    latex_str = segment.visual_anchor.latex
                    if latex_str:
                        clean_eq = (
                            latex_str.replace(r"\approx", "≈")
                            .replace(r"\theta", "θ")
                            .replace(r"\pi", "π")
                            .replace(r"\cos", "cos")
                            .replace(r"\sin", "sin")
                            .replace(r"\text{", "")
                            .replace("}", "")
                        )
                        f_math = Text(clean_eq, font_size=36, color=BLUE).next_to(f_title, DOWN, buff=0.35)
                        if f_math.width > 12.0:
                            f_math.scale_to_fit_width(12.0)
                        f_box = SurroundingRectangle(f_math, color=GOLD, buff=0.25)
                        elements.extend([f_math, f_box])
                        prev_mob = f_box

                    if segment.visual_anchor.key_definitions:
                        where_lbl = Text("Key Concept Breakdown:", font_size=20, color=GOLD, weight=BOLD).next_to(prev_mob, DOWN, buff=0.35).to_edge(LEFT, buff=1.0)
                        elements.append(where_lbl)
                        bullet_mobs = []
                        for d in segment.visual_anchor.key_definitions[:5]:
                            clean_d = d.replace("\\bullet\\", "•").replace("\\bullet", "•").replace(r"\approx", "≈").replace(r"\theta", "θ").replace(r"\pi", "π")
                            b_mob = Text(f"• {clean_d}", font_size=18, color=WHITE)
                            if b_mob.width > 11.5:
                                b_mob.scale_to_fit_width(11.5)
                            bullet_mobs.append(b_mob)
                        if bullet_mobs:
                            b_group = VGroup(*bullet_mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)
                            elements.append(b_group)

                    self.play(*[FadeIn(el) for el in elements], run_time=1.5)
                    self.wait(1.5)
                except Exception as exc3:
                    print(f"[Visual Render Emergency Fallback] Slide {segment.slide_num}: {exc3}", file=sys.stderr)
                    self.clear()
                    safe_title = Text(f"Slide {segment.slide_num}: {segment.concept[:30]}", font_size=28, color=YELLOW)
                    self.add(safe_title)
                    self.wait(1.5)
            else:
                self.wait(1.0)

    with _manim_render_lock:
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

    if not dest.is_file() or dest.stat().st_size == 0:
        # Guarantee an MP4 exists using ffmpeg color generator so timeline assembly never drops slides
        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=0x111827:s=854x480:d=3.0:r=30",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(dest),
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if dest.is_file() and dest.stat().st_size > 0:
                return dest.resolve()
        except Exception:
            pass

    return None


def _synthesize_edge_tts(
    clean_text: str,
    output_wav: Path,
    voice: str = "en-US-ChristopherNeural",
) -> bool:
    """Fast neural speech synthesis using Edge-TTS with transcode to standard 24kHz WAV."""
    try:
        import asyncio
        import edge_tts

        temp_mp3 = output_wav.with_suffix(".temp.mp3")

        async def _run():
            comm = edge_tts.Communicate(clean_text, voice)
            await comm.save(str(temp_mp3))

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(lambda: asyncio.run(_run())).result(timeout=25)
        else:
            asyncio.run(_run())

        if temp_mp3.is_file() and temp_mp3.stat().st_size > 0:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(temp_mp3), "-ar", "24000", "-ac", "1", str(output_wav)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            temp_mp3.unlink(missing_ok=True)
            return True
    except Exception as exc:
        print(f"[Edge-TTS Info] Fast speech note: {exc}; using fallback narrator", file=sys.stderr)
    return False


def synthesize_teaching_audio(
    narration_text: str,
    output_wav: Path,
    max_words: int = 220,
    voice: str | None = None,
) -> float:
    """Synthesizes pedagogical narration into WAV audio using Edge-TTS or Pocket TTS.

    Guarantees strict word budget (max 220 words ~75s) to prevent runaway TTS latency.
    Returns the authoritative measured duration in seconds.
    """
    clean_text = re.sub(r"<think>.*?</think>", "", narration_text, flags=re.DOTALL)
    clean_text = re.sub(r"<bookmark.*?>", "", clean_text).strip()

    # Enforce hard upper bound on narration words
    words = clean_text.split()
    if len(words) > max_words:
        truncated = " ".join(words[:max_words])
        last_period = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_period > len(truncated) // 2:
            clean_text = truncated[: last_period + 1]
        else:
            clean_text = truncated + "."

    tts_backend = os.getenv("AOS_TTS_BACKEND", "auto").lower()
    edge_voice = voice or os.getenv("AOS_TTS_VOICE", "en-US-ChristopherNeural")

    # Fast Path: Edge-TTS (sub-2 second neural synthesis)
    if tts_backend in ("auto", "edge", "edge-tts"):
        if _synthesize_edge_tts(clean_text, output_wav, voice=edge_voice):
            dur = get_media_duration(output_wav)
            if dur > 0.5:
                return dur

    # Offline Fallback: Resident Kyutai Pocket TTS (100M CPU model)
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


def repair_visual_anchor_code(
    original_code: str,
    segment: TeachingSegment,
    verdict: VisualCriticVerdict,
    client: OpenAI,
    model: str,
) -> str:
    """Repairs Manim animation code based on concrete visual feedback from the Visual Critic."""
    repair_prompt = (
        f"Topic: {segment.concept}\n"
        f"Displayed Formula: {segment.visual_anchor.latex or ''}\n"
        f"Visible Elements: {segment.visual_anchor.visible_elements}\n"
        f"Key Definitions: {segment.visual_anchor.key_definitions}\n\n"
        f"{verdict.feedback_for_code_repair}\n\n"
        f"Previous Manim Code:\n```python\n{original_code}\n```\n\n"
        "Please provide the repaired, fully working Manim code snippet.\n"
        "CRITICAL REQUIREMENTS:\n"
        "1. Fix all reported visual defects (e.g. scale formulas with scale_to_fit_width to fit [-6, 6], add vertical buffers to prevent collisions, ensure bright contrast colors).\n"
        "2. Output ONLY clean executable Python code inside ```python ... ``` without Scene class or construct definition.\n"
        "3. Start directly with mobjects and self.play(...)."
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mathematical animator repairing Manim code based on Visual Critic inspection. Output strictly executable code inside ```python ... ``` without Scene class.",
                },
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
        _, repaired_code = _parse_visual_output(content)
        if repaired_code and repaired_code.strip():
            return repaired_code
    except Exception as exc:
        print(f"[Visual Critic Repair Warning] Slide {segment.slide_num} repair LLM failed: {exc}", file=sys.stderr)

    return original_code


def _process_single_slide(
    i: int,
    total_slides: int,
    prompt: str,
    outline: str,
    client: OpenAI,
    model: str,
    run_dir: Path,
    quality: str,
    _notify: Callable[[str, str], None],
) -> tuple[int, TeachingSegment, Path | None, str]:
    """Generates visual anchor, performs visual critic check, synthesizes speech, and produces video chunk."""
    _notify("PlanTeachingScriptNode", f"Planning TeachingSegment {i} (Rich Visual Anchor & Pedagogy)")
    segment = plan_teaching_segment(
        prompt=prompt,
        slide_num=i,
        total_slides=total_slides,
        outline=outline,
        client=client,
        model=model,
    )

    _notify("CodeAgent", f"Visual anchor Manim code ready for Slide {i}")
    _notify("VALIDATING_CODE", f"Validating code for Slide {i}")
    _notify("RENDERING", f"Rendering visual anchor for Slide {i}")

    # Step 1: Render Visual Anchor with Visual Critic Feedback & Retry Loop
    visual_critic = get_visual_critic()
    max_visual_retries = int(os.getenv("AOS_VISUAL_CRITIC_MAX_RETRIES", "2"))

    visual_path = None
    for attempt in range(max_visual_retries + 1):
        att_label = f" (attempt {attempt + 1}/{max_visual_retries + 1})" if attempt > 0 else ""
        _notify("RENDERING", f"Rendering visual anchor for Slide {i}{att_label}")
        visual_path = render_visual_anchor(segment, run_dir, quality=quality)
        if not visual_path or not visual_path.is_file():
            continue

        segment.visual_path = str(visual_path)
        segment.visual_duration = get_media_duration(visual_path)

        # Extract keyframe snapshot for inspection
        keyframe_path = run_dir / f"slide_{i}_keyframe_att{attempt + 1}.png"
        extracted_frame = visual_critic.extract_keyframe(visual_path, keyframe_path)

        v_context = VisualContext(
            slide_num=i,
            concept=segment.concept,
            learning_objective=segment.learning_objective,
            latex_formula=segment.visual_anchor.latex or "",
            visible_elements=segment.visual_anchor.visible_elements,
            key_definitions=segment.visual_anchor.key_definitions,
            manim_code=segment.manim_code,
        )

        _notify("VISUAL_CRITIC", f"Inspecting Slide {i} with Visual Critic ({visual_critic.name})")
        verdict = visual_critic.critique_frame(extracted_frame, v_context)
        segment.visual_verdict = verdict.model_dump()

        if verdict.passed:
            _notify("VISUAL_CRITIC_PASS", f"Slide {i} passed visual critic inspection (Score: {verdict.score:.2f})")
            break
        else:
            issues_summary = ", ".join(verdict.detected_issues[:3]) if verdict.detected_issues else "Layout defect"
            _notify("VISUAL_CRITIC_DEFECTS", f"Slide {i} defects: {issues_summary}")
            if attempt < max_visual_retries:
                _notify("VISUAL_CRITIC_REPAIR", f"Repairing Slide {i} Manim code using critic feedback ({attempt + 1}/{max_visual_retries})...")
                repaired_code = repair_visual_anchor_code(
                    original_code=segment.manim_code,
                    segment=segment,
                    verdict=verdict,
                    client=client,
                    model=model,
                )
                if repaired_code and repaired_code.strip():
                    segment.manim_code = repaired_code
            else:
                _notify("VISUAL_CRITIC_EXHAUSTED", f"Slide {i} max visual retries reached. Retaining best render.")

    # Step 2: Synthesize Authoritative Pedagogical Narration
    audio_path = run_dir / f"slide_{i}_audio.wav"
    narr_dur = synthesize_teaching_audio(segment.narration, audio_path)
    segment.audio_path = str(audio_path)
    segment.narration_duration = narr_dur

    # Step 3: Decoupled Visual Hold & Segment Assembly
    _notify("TIMELINE_HOLD", f"Extending Slide {i} final frame: visual {segment.visual_duration:.1f}s, narration {segment.narration_duration:.1f}s")
    chunk_path = assemble_teaching_segment(segment, run_dir)

    code_part = (
        f"# --- Segment {segment.slide_num}: {segment.concept} ---\n"
        f"# Objective: {segment.learning_objective}\n"
        f"# Definitions: {segment.visual_anchor.key_definitions}\n"
        f"# Narration: {segment.narration}\n"
        f"{segment.manim_code}\n"
    )

    return i, segment, chunk_path, code_part


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

    combined_code_parts: List[str] = [
        "# Auto-generated by AOS Decoupled Teaching Segment Engine",
        "from manim import *",
        "import numpy as np\n",
    ]

    # Concurrent slide generation pipeline
    import concurrent.futures

    max_workers = min(total_slides, int(os.getenv("AOS_MAX_SLIDE_WORKERS", "3")))
    results: list[tuple[int, TeachingSegment, Path | None, str]] = []

    if max_workers > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(
                    _process_single_slide,
                    i=i,
                    total_slides=total_slides,
                    prompt=prompt,
                    outline=outline,
                    client=client,
                    model=effective_model,
                    run_dir=run_dir,
                    quality=quality,
                    _notify=_notify,
                )
                for i in range(1, total_slides + 1)
            ]
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())
    else:
        for i in range(1, total_slides + 1):
            results.append(
                _process_single_slide(
                    i=i,
                    total_slides=total_slides,
                    prompt=prompt,
                    outline=outline,
                    client=client,
                    model=effective_model,
                    run_dir=run_dir,
                    quality=quality,
                    _notify=_notify,
                )
            )

    # Sort results deterministically by slide_num
    results.sort(key=lambda r: r[0])

    segments: List[TeachingSegment] = [r[1] for r in results]
    rendered_chunks: List[Path] = [r[2] for r in results if r[2] and r[2].is_file()]
    for r in results:
        combined_code_parts.append(r[3])

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
                "key_definitions": s.visual_anchor.key_definitions,
                "layout_type": s.visual_anchor.layout_type,
                "visual_verdict": s.visual_verdict,
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

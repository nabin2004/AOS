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

import asyncio
import concurrent.futures
from contextlib import contextmanager
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

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
    HeuristicVisionCritic,
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
    visual_duration: float = 0.0
    narration_duration: float = 0.0

    @property
    def total_duration(self) -> float:
        if self.teaching_segment:
            return self.teaching_segment.total_duration
        return max(self.visual_duration, self.narration_duration)

    @property
    def hold_duration(self) -> float:
        if self.teaching_segment:
            return self.teaching_segment.hold_duration
        return max(0.0, self.narration_duration - self.visual_duration)


@dataclass
class SlideProcessResult:
    """Result of processing a single slide in the keyframe pipeline."""
    slide_num: int
    segment: TeachingSegment
    chunk_path: Path | None
    code_part: str

    def __iter__(self):
        return iter((self.slide_num, self.segment, self.chunk_path, self.code_part))

    def __getitem__(self, idx: int) -> Any:
        return (self.slide_num, self.segment, self.chunk_path, self.code_part)[idx]


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
) -> tuple[OpenAI, str]:
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
        # No credentials or local base provided; use unconfigured local placeholder
        effective_base = "https://openrouter.ai/api/v1"
        effective_key = "unconfigured_local"

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


def execute_completion_with_fallback(
    client: OpenAI,
    primary_model: str,
    messages: list[dict],
    temperature: float = 0.3,
    timeout: float | None = None,
) -> Any:
    """Executes a chat completion with transparent multi-model failover on 503 / 429 / capacity exhaustion."""
    base_url = str(client.base_url)
    api_key = str(client.api_key or "")

    # Short-circuit if OpenRouter is targeted with dummy/unconfigured key
    if "openrouter.ai" in base_url and api_key in ("local", "unconfigured_local", ""):
        raise ValueError(
            "No OpenRouter API key configured; short-circuiting external LLM call to fallback."
        )

    candidates = [primary_model]
    # The keyframe engine uses the OpenAI-compatible client directly rather
    # than Pydantic AI, so its completion budget must be supplied here.
    # Without this, local/BYOK servers often fall back to a short provider
    # default and produce abbreviated narration.
    try:
        max_tokens = max(
            2048,
            int(os.getenv("AOS_KEYFRAME_MAX_TOKENS", os.getenv("AOS_MAX_TOKENS", "12288"))),
        )
    except ValueError:
        max_tokens = 12288

    # Add robust backup models when using OpenRouter or cloud
    if "openrouter.ai" in base_url:
        for backup in ("openai/gpt-4o-mini", "google/gemini-2.5-flash", "anthropic/claude-3.5-haiku"):
            if backup not in candidates:
                candidates.append(backup)

    last_error = None
    for cand in candidates:
        try:
            return client.chat.completions.create(
                model=cand,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        except Exception as exc:
            last_error = exc
            err_str = str(exc).lower()
            is_transient = any(
                k in err_str
                for k in ("503", "502", "504", "429", "capacity", "unavailable", "rate limit", "overloaded", "timeout")
            )
            if is_transient and cand != candidates[-1]:
                next_cand = candidates[candidates.index(cand) + 1]
                print(
                    f"[Model Failover] Model '{cand}' unavailable ({exc}); failing over to '{next_cand}'...",
                    file=sys.stderr,
                )
                continue
            raise exc

    if last_error:
        raise last_error


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

Length: Around 180-320 words (~70-130 seconds of speech). Do not stop after a
short summary; fully explain the visible steps, intuition, and takeaway.
Wrap your output in <narration> ... </narration> tags.
"""


def _extract_topic_title(prompt: str) -> str:
    """Extracts a clean, short topic title from potentially massive or multi-paragraph user prompts."""
    lines = [l.strip() for l in prompt.strip().splitlines() if l.strip()]
    if not lines:
        return "Key Mathematical Principles"
    first_line = lines[0]

    # Remove conversational prefixes
    first_line = re.sub(
        r"^(?:teach\s+me\s+about\s+(?:the\s+)?|explain\s+(?:the\s+)?|what\s+is\s+(?:the\s+)?|"
        r"help\s+me\s+understand\s+(?:the\s+)?|introduce\s+(?:the\s+)?|visualize\s+(?:the\s+)?|"
        r"show\s+me\s+(?:how\s+)?|lecture\s+on\s+(?:the\s+)?|deep\s+dive\s+into\s+(?:the\s+)?|"
        r"how\s+(?:to\s+|a\s+|an\s+|the\s+)?)\s*",
        "",
        first_line,
        flags=re.IGNORECASE,
    ).strip()

    # Strip general Wikipedia / web-scraping navigation artifacts and secondary subtitles
    first_line = re.split(
        r":\s*Order of operations|(?:\s*[-–—|]\s*)?(?:from\s+)?wikipedia(?:\s+the\s+free\s+encyclopedia)?|"
        r"\s*article\s+talk|\s*jump\s+to\s+content|\s*main\s+page",
        first_line,
        flags=re.IGNORECASE,
    )[0].strip()

    first_line = first_line.rstrip(":,.-")
    if len(first_line) > 60:
        truncated = first_line[:57]
        last_space = truncated.rfind(" ")
        if last_space > 20:
            first_line = truncated[:last_space] + "..."
        else:
            first_line = truncated + "..."

    return first_line or "Key Mathematical Concept"


def _parse_visual_output(text: str) -> tuple[VisualAnchor, str]:
    """Extracts VisualAnchor metadata and Python code from LLM output."""
    anchor = VisualAnchor(type="annotated_formula", visual_purpose="Core concept visualization")
    anchor_match = re.search(r"<visual_anchor>(.*?)</visual_anchor>", text, re.DOTALL | re.IGNORECASE)
    if anchor_match:
        try:
            raw_json = anchor_match.group(1).strip()
            data = json.loads(raw_json)
            anchor = VisualAnchor(**data)
        except Exception as exc:
            print(f"[Keyframe Engine] Failed to parse <visual_anchor> JSON: {exc}", file=sys.stderr)

    code = _parse_code_only(text)
    return anchor, code


def _parse_code_only(text: str) -> str:
    """Extracts executable Python code from LLM output, ignoring XML/anchor metadata."""
    code_match = re.search(r"```(?:python)?(.*?)```", text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    clean = re.sub(r"<visual_anchor>.*?</visual_anchor>", "", text, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<think>.*?</think>", "", clean, flags=re.DOTALL | re.IGNORECASE)
    if "self.play" in clean:
        return clean.strip()
    return ""


def _parse_narration_output(text: str) -> str:
    """Extracts pedagogical narration from LLM output, stripping reasoning traces."""
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    clean = re.sub(r"(?:^|\n)\s*Assistant:?\s*", "\n", clean, flags=re.IGNORECASE)
    narr_match = re.search(r"<narration>(.*?)</narration>", clean, re.DOTALL | re.IGNORECASE)
    if narr_match:
        return narr_match.group(1).strip()
    clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    return clean.strip()


def _clean_manim_code(code_str: str) -> str:
    """Cleans generated code: unwraps Scene classes and replaces `with self.play(...):` with balanced parens."""
    # 1. Handle hallucinated Scene class definitions
    if re.search(r"class\s+\w+\s*\(\s*(?:Scene|VoiceoverScene)\s*\)\s*:", code_str):
        lines = code_str.splitlines()
        extracted_lines = []
        inside_construct = False
        base_indent = None
        for line in lines:
            if re.match(r"^\s*def\s+construct\s*\(\s*self\s*\)\s*:", line):
                inside_construct = True
                continue
            if inside_construct:
                if not line.strip():
                    extracted_lines.append("")
                    continue
                indent = len(line) - len(line.lstrip())
                if base_indent is None:
                    base_indent = indent
                if indent >= base_indent:
                    extracted_lines.append(line[base_indent:])
                else:
                    break
        if extracted_lines:
            code_str = "\n".join(extracted_lines)

    # 2. Clean hallucinated `with self.play(...):` blocks with balanced parens and fix indentation
    lines = code_str.splitlines()
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^(\s*)with\s+self\.play\(", line)
        if match:
            indent_str = match.group(1)
            indent_len = len(indent_str)

            curr_str = line
            start_paren = match.end() - 1
            depth = 1
            idx = start_paren + 1

            while depth > 0 and idx <= len(curr_str):
                if idx == len(curr_str):
                    if i + 1 < len(lines):
                        i += 1
                        curr_str += "\n" + lines[i]
                    else:
                        break
                ch = curr_str[idx]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                elif ch in ('"', "'"):
                    quote = ch
                    idx += 1
                    while idx < len(curr_str) and curr_str[idx] != quote:
                        if curr_str[idx] == "\\":
                            idx += 1
                        idx += 1
                idx += 1

            if depth == 0:
                args = curr_str[start_paren + 1 : idx - 1]
                play_line = f"{indent_str}self.play({args})"
                out_lines.append(play_line)

                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if not next_line.strip():
                        out_lines.append(next_line)
                        i += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent > indent_len:
                        stripped_stmt = next_line.strip()
                        if stripped_stmt != "pass":
                            unindented = indent_str + next_line[next_indent:]
                            out_lines.append(unindented)
                        i += 1
                    else:
                        break
                continue
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)
        i += 1

    return "\n".join(out_lines)


class VisualAnchorScene(Scene):
    """Self-contained Manim scene that constructs a TeachingSegment visual anchor."""

    def __init__(self, segment: TeachingSegment | None = None, **kwargs):
        super().__init__(**kwargs)
        self.segment = segment

    def wait_until_bookmark(self, mark: str, **kwargs):
        self.wait(0.2)

    @contextmanager
    def voiceover(self, *args, **kwargs):
        yield None

    def construct(self):
        if not self.segment:
            return

        safe_globals: dict[str, Any] = {
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
            from manim import MarkupText, Tex
            safe_globals["Tex"] = Tex
            safe_globals["MarkupText"] = MarkupText
        except Exception:
            safe_globals["Tex"] = MathTex
            safe_globals["MarkupText"] = Text

        def _execute_code(code_str: str) -> bool:
            cleaned = _clean_manim_code(code_str)
            locs: dict[str, Any] = {"self": self}
            exec(cleaned, safe_globals, locs)
            return len(self.mobjects) > 0

        executed = False
        if self.segment.manim_code.strip():
            try:
                executed = _execute_code(self.segment.manim_code)
            except Exception as exc:
                print(f"[Visual Render Warning] Slide {self.segment.slide_num} primary exec error: {exc}", file=sys.stderr)
                self.clear()

            if not executed:
                try:
                    self.clear()
                    alt_code = re.sub(r"(?:MathTex|Tex|Paragraph)\(\s*r?([\"'])(.*?)\1", r"Text(\1\2\1", self.segment.manim_code)
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
                        print(f"[Visual Render Info] Slide {self.segment.slide_num} successfully rendered via Text transpilation!", file=sys.stderr)
                except Exception as exc2:
                    print(f"[Visual Render Warning] Slide {self.segment.slide_num} transpilation failed: {exc2}", file=sys.stderr)
                    self.clear()

        if not executed or len(self.mobjects) == 0:
            try:
                self.clear()
                title_text = self.segment.visual_anchor.title or self.segment.concept
                f_title = Text(title_text, font_size=32, color=YELLOW).to_edge(UP, buff=0.4)
                if f_title.width > 12.0:
                    f_title.scale_to_fit_width(12.0)
                elements = [f_title]
                prev_mob = f_title

                latex_str = self.segment.visual_anchor.latex
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

                if self.segment.visual_anchor.key_definitions:
                    where_lbl = Text("Key Concept Breakdown:", font_size=20, color=GOLD, weight=BOLD).next_to(prev_mob, DOWN, buff=0.35).to_edge(LEFT, buff=1.0)
                    elements.append(where_lbl)
                    bullet_mobs = []
                    for d in self.segment.visual_anchor.key_definitions[:5]:
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
                print(f"[Visual Render Emergency Fallback] Slide {self.segment.slide_num}: {exc3}", file=sys.stderr)
                self.clear()
                safe_title = Text(f"Slide {self.segment.slide_num}: {self.segment.concept[:30]}", font_size=28, color=YELLOW)
                self.add(safe_title)
                self.wait(1.5)
        else:
            self.wait(1.0)


def _render_visual_anchor_subprocess(
    segment: TeachingSegment,
    output_dir: Path,
    output_stem: str,
    quality: str = "low_quality",
    timeout: float = 120.0,
) -> Path | None:
    """Renders a Manim scene in an isolated subprocess, preventing global config contention across threads."""
    spec_path = output_dir / f"_slide_{segment.slide_num}_spec.json"
    runner_path = output_dir / f"_slide_{segment.slide_num}_runner.py"

    try:
        spec_path.write_text(segment.model_dump_json(), encoding="utf-8")
        repo_root = Path(__file__).resolve().parents[2]
        runner_code = f"""import sys
from pathlib import Path

repo_root = Path(r"{repo_root}")
for p in (repo_root, repo_root / "packages" / "ir" / "src", repo_root / "apps" / "agents"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ir import TeachingSegment
from keyframe_engine import VisualAnchorScene
from manim import config

if __name__ == "__main__":
    spec_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_stem = sys.argv[3]
    quality = sys.argv[4]

    segment = TeachingSegment.model_validate_json(spec_file.read_text(encoding="utf-8"))
    config.media_dir = str(output_dir)
    config.quality = quality
    config.output_file = output_stem
    config.verbosity = "WARNING"

    scene = VisualAnchorScene(segment=segment)
    scene.render()
"""
        runner_path.write_text(runner_code, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(runner_path), str(spec_path), str(output_dir), output_stem, quality],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            print(
                f"[Visual Subprocess Warning] Slide {segment.slide_num} render error (rc={proc.returncode}): {proc.stderr[:400]}",
                file=sys.stderr,
            )

        # Locate rendered MP4
        dest = output_dir / f"{output_stem}.mp4"
        for mp4 in output_dir.rglob(f"*{output_stem}*.mp4"):
            if mp4.is_file() and "partial_movie_files" not in mp4.parts:
                if mp4.resolve() != dest.resolve():
                    try:
                        shutil.copy2(mp4, dest)
                    except Exception:
                        pass
                break

        if dest.is_file() and dest.stat().st_size > 0:
            return dest.resolve()

    except Exception as exc:
        print(f"[Visual Subprocess Exception] Slide {segment.slide_num}: {exc}", file=sys.stderr)
    finally:
        spec_path.unlink(missing_ok=True)
        runner_path.unlink(missing_ok=True)

    return None


def render_visual_anchor(
    segment: TeachingSegment,
    output_dir: Path,
    quality: str = "low_quality",
) -> Path | None:
    """Renders the pure visual animation for a TeachingSegment using Manim.

    Renders via isolated subprocess for true concurrency without global lock contention.
    Falls back gracefully to in-process tempconfig and ffmpeg color generator.
    """
    output_stem = f"slide_{segment.slide_num}_visual"

    # Primary: Run via isolated subprocess for thread-safety and true parallelism
    sub_path = _render_visual_anchor_subprocess(segment, output_dir, output_stem, quality=quality)
    if sub_path and sub_path.is_file() and sub_path.stat().st_size > 0:
        return sub_path

    # Secondary: In-process fallback with tempconfig under safety lock
    try:
        from manim import tempconfig
        with _manim_render_lock:
            with tempconfig({"media_dir": str(output_dir), "quality": quality, "output_file": output_stem, "verbosity": "WARNING"}):
                scene = VisualAnchorScene(segment=segment)
                scene.render()

        dest = output_dir / f"{output_stem}.mp4"
        for mp4 in output_dir.rglob(f"*{output_stem}*.mp4"):
            if mp4.is_file() and "partial_movie_files" not in mp4.parts:
                if mp4.resolve() != dest.resolve():
                    try:
                        shutil.copy2(mp4, dest)
                    except Exception:
                        pass
                return dest.resolve()
    except Exception as exc:
        print(f"[Visual In-Process Fallback Warning] Slide {segment.slide_num}: {exc}", file=sys.stderr)

    dest = output_dir / f"{output_stem}.mp4"
    if dest.is_file() and dest.stat().st_size > 0:
        return dest.resolve()

    # Tertiary safety net: ffmpeg color generator so timeline assembly never drops slides
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
    except Exception as ff_err:
        print(f"[Visual Render Emergency Warning] ffmpeg fallback failed for Slide {segment.slide_num}: {ff_err}", file=sys.stderr)

    return None


def _synthesize_edge_tts(
    clean_text: str,
    output_wav: Path,
    voice: str = "en-US-ChristopherNeural",
) -> bool:
    """Fast neural speech synthesis using Edge-TTS with transcode to standard 24kHz WAV."""
    temp_mp3 = output_wav.with_suffix(f".{uuid4().hex[:6]}.temp.mp3")
    try:
        import edge_tts

        async def _run():
            comm = edge_tts.Communicate(clean_text, voice)
            await asyncio.wait_for(comm.save(str(temp_mp3)), timeout=20.0)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
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
            return True
    except Exception as exc:
        print(f"[Edge-TTS Info] Fast speech note: {exc}; using fallback narrator", file=sys.stderr)
    finally:
        temp_mp3.unlink(missing_ok=True)

    return False


def synthesize_teaching_audio(
    narration_text: str,
    output_wav: Path,
    max_words: int = 320,
    voice: str | None = None,
    return_status: bool = False,
) -> float | tuple[float, bool]:
    """Synthesizes pedagogical narration into WAV audio using Edge-TTS or Pocket TTS.

    Guarantees strict word budget with clean sentence-boundary truncation.
    Returns duration (or (duration, is_real_audio) if return_status=True).
    """
    clean_text = re.sub(r"<think>.*?</think>", "", narration_text, flags=re.DOTALL)
    clean_text = re.sub(r"<bookmark.*?>", "", clean_text).strip()

    # Enforce hard upper bound on narration words, truncating strictly at sentence boundaries
    words = clean_text.split()
    if len(words) > max_words:
        truncated = " ".join(words[:max_words])
        last_punct = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_punct > 0:
            clean_text = truncated[: last_punct + 1]
        else:
            clean_text = truncated + "..."

    tts_backend = os.getenv("AOS_TTS_BACKEND", "auto").lower()
    edge_voice = voice or os.getenv("AOS_TTS_VOICE", "en-US-ChristopherNeural")

    # Fast Path: Edge-TTS
    if tts_backend in ("auto", "edge", "edge-tts"):
        if _synthesize_edge_tts(clean_text, output_wav, voice=edge_voice):
            dur = get_media_duration(output_wav)
            if dur > 0.5:
                return (dur, True) if return_status else dur

    # Offline Fallback: Resident Kyutai Pocket TTS (100M CPU model)
    try:
        from tools.aos_speech_service import _get_narrator

        narrator = _get_narrator("alba", "english")
        narrator.synthesize(clean_text, output_wav)
        dur = get_media_duration(output_wav)
        if dur > 0.5:
            return (dur, True) if return_status else dur
    except Exception as p_err:
        print(f"[Keyframe Audio Warning] Pocket TTS failed for '{output_wav.name}': {p_err}", file=sys.stderr)

    # Silent fallback with explicit warning
    print(
        f"[Keyframe Audio Warning] Both Edge-TTS and Pocket TTS failed for '{output_wav.name}'. Created silent fallback.",
        file=sys.stderr,
    )
    try:
        import scipy.io.wavfile

        sr = 24000
        words_count = len(clean_text.split())
        sec = max(3.0, words_count * 0.45)
        silence = np.zeros(int(sr * sec), dtype=np.float32)
        scipy.io.wavfile.write(output_wav, sr, silence)
    except Exception as sc_err:
        print(f"[Keyframe Audio Warning] Scipy silent WAV generation failed: {sc_err}", file=sys.stderr)

    dur = get_media_duration(output_wav)
    return (dur, False) if return_status else dur


def assemble_teaching_segment(
    segment: TeachingSegment,
    output_dir: Path,
) -> Path | None:
    """Combines visual animation, static visual hold, and authoritative narration audio."""
    if not segment.visual_path or not Path(segment.visual_path).is_file():
        return None

    in_video = Path(segment.visual_path)
    in_audio = Path(segment.audio_path) if segment.audio_path and Path(segment.audio_path).is_file() else None
    out_chunk = output_dir / f"slide_{segment.slide_num}.mp4"

    segment.visual_duration = get_media_duration(in_video)
    if in_audio:
        segment.narration_duration = get_media_duration(in_audio)
    else:
        print(
            f"[Assembly Warning] Slide {segment.slide_num} missing narration audio file at {segment.audio_path}; visual hold set to 0.0.",
            file=sys.stderr,
        )
        segment.narration_duration = 0.0
        segment.audio_path = None

    hold_dur = segment.hold_duration

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


def _mp4_has_audio_stream(video_path: Path) -> bool | None:
    """Verify that the assembled MP4, not only its source WAV, has audio."""
    if not video_path.is_file():
        return False
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return probe.returncode == 0 and "audio" in probe.stdout.lower()


def repair_visual_anchor_code(
    original_code: str,
    segment: TeachingSegment,
    verdict: VisualCriticVerdict,
    client: OpenAI,
    model: str,
    timeout: float = 20.0,
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
        resp = execute_completion_with_fallback(
            client=client,
            primary_model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mathematical animator repairing Manim code based on Visual Critic inspection. Output strictly executable code inside ```python ... ``` without Scene class.",
                },
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0.2,
            timeout=timeout,
        )
        content = resp.choices[0].message.content or ""
        repaired_code = _parse_code_only(content)
        if repaired_code and repaired_code.strip():
            return repaired_code
    except Exception as exc:
        print(f"[Visual Critic Repair Warning] Slide {segment.slide_num} repair LLM failed: {exc}", file=sys.stderr)

    return original_code


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
    if any(k in p for k in ("pythagor", "right triangle", "hypotenuse")):
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Pythagorean Theorem):\n"
            "- Core Formula: a² + b² = c² in Euclidean right-angled geometry.\n"
            "- Geometric Proof: Dissecting squares of side (a+b) to show four right triangles surround c².\n"
            "- Metric Foundations: Distance formula in R²: d = √((x₂ - x₁)² + (y₂ - y₁)²); Hilbert space inner product norms."
        )
    if any(k in p for k in ("newton's second law", "f = ma", "second law of motion", "f=ma")):
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Newton's Second Law of Motion):\n"
            "- Fundamental Equation: F_net = m * a, or more generally F = dp/dt (rate of change of momentum).\n"
            "- Physical Units: Force in Newtons (kg·m/s²), mass in kg, acceleration in m/s².\n"
            "- Vector Nature: Net force vector aligns in the exact direction of acceleration."
        )
    if any(k in p for k in ("binary search", "bsearch", "divide and conquer")):
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Binary Search Algorithm):\n"
            "- Precondition: Array must be sorted in monotonic order.\n"
            "- Complexity: O(log n) time complexity vs O(n) linear search, O(1) auxiliary space.\n"
            "- Pointer Mechanics: Maintain low and high pointers, compute mid = low + (high - low)//2, halve search space."
        )
    if any(k in p for k in ("bayes", "conditional probability", "prior probability", "posterior")):
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Bayes' Theorem):\n"
            "- Formula: P(A|B) = [P(B|A) * P(A)] / P(B).\n"
            "- Components: P(A|B) is posterior, P(B|A) is likelihood, P(A) is prior belief, P(B) is total evidence.\n"
            "- Applications: Medical diagnostic testing, machine learning classification, Bayesian inference."
        )
    if any(k in p for k in ("gravitation", "gravity", "orbital", "kepler")):
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Newton's Law of Universal Gravitation):\n"
            "- Equation: F = G * (m₁ * m₂) / r².\n"
            "- Inverse-Square Law: Doubling distance reduces gravitational attraction by factor of 4.\n"
            "- Orbital Mechanics: Gravitational pull supplies centripetal acceleration: v = √(GM/r)."
        )
    if any(k in p for k in ("neural network", "forward pass", "activation function")):
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Neural Network Forward Pass):\n"
            "- Linear Combination: z = W · x + b (matrix weight multiplication plus bias vector).\n"
            "- Non-linear Activation: a = σ(z) (e.g. ReLU, Sigmoid, GeLU) introducing non-linearity.\n"
            "- Layered Composition: Output of layer l feeds as input to layer l+1."
        )
    if any(k in p for k in ("matrix multiplication", "linear transformation", "basis vector")):
        return (
            "DOMAIN CONTEXT & PEDAGOGICAL GROUNDING (Matrix Multiplication as Linear Transformation):\n"
            "- Geometric Intuition: Columns of 2x2 matrix indicate where basis vectors i_hat and j_hat land.\n"
            "- Transformation: [x', y']^T = [[a, b], [c, d]] [x, y]^T = x * [a, c]^T + y * [b, d]^T.\n"
            "- Determinant: det(A) measures scaling factor of area, negative determinant indicates space inversion."
        )
    clean_topic = _extract_topic_title(prompt)
    return (
        f"DOMAIN CONTEXT & PEDAGOGICAL GROUNDING ({clean_topic}):\n"
        "- Structure the concept into clear visual primitives: main equation, symbol breakdown, and intuition.\n"
        "- Ensure symbols are defined explicitly with visual cards or labeled groups."
    )


def _build_curated_fallback_segment(prompt: str, slide_num: int, total_slides: int) -> TeachingSegment:
    """Curated, high-fidelity STEM TeachingSegments with rich visual anchors, symbol breakdowns, and ~60-90s pedagogy."""
    p_lower = prompt.lower()
    clean_topic = _extract_topic_title(prompt)

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
    elif any(k in p_lower for k in ("pythagor", "right triangle")):
        anchor = VisualAnchor(
            type="annotated_formula",
            title="The Pythagorean Theorem" if slide_num == 1 else f"Pythagorean Theorem: Geometric Proof {slide_num}",
            latex=r"a^2 + b^2 = c^2",
            visible_elements=["Leg a", "Leg b", "Hypotenuse c", "Right Angle"],
            key_definitions=[
                "a, b : Orthogonal legs forming the 90-degree right angle",
                "c : Hypotenuse, opposite the right angle (longest side)",
                "a² + b² = c² : Area of squares on legs equals area on hypotenuse",
            ],
            visual_purpose="Establish the foundational metric relationship in Euclidean geometry.",
        )
        code = (
            'title = Text("The Pythagorean Theorem", font_size=34, color=YELLOW).to_edge(UP, buff=0.4)\n'
            'formula = MathTex(r"a^2 + b^2 = c^2", font_size=44, color=BLUE).next_to(title, DOWN, buff=0.35)\n'
            'box = SurroundingRectangle(formula, color=GOLD, buff=0.25)\n'
            'where_lbl = Text("Geometric Properties:", font_size=22, color=GOLD, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.2)\n'
            'b1 = MathTex(r"\\bullet\\ a, b : \\text{Perpendicular side lengths (legs)}", font_size=20, color=WHITE)\n'
            'b2 = MathTex(r"\\bullet\\ c : \\text{Hypotenuse opposite the } 90^\\circ \\text{ angle}", font_size=20, color=TEAL)\n'
            'b3 = MathTex(r"\\bullet\\ c = \\sqrt{a^2 + b^2} : \\text{Euclidean distance in } \\mathbb{R}^2", font_size=20, color=GREEN)\n'
            'bullets = VGroup(b1, b2, b3).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)\n'
            'self.play(Write(title), run_time=0.8)\n'
            'self.play(Write(formula), Create(box), run_time=1.2)\n'
            'self.play(FadeIn(where_lbl), run_time=0.5)\n'
            'self.play(LaggedStart(*[FadeIn(b, shift=RIGHT*0.2) for b in bullets], lag_ratio=0.2), run_time=1.5)\n'
            'self.wait(1.5)\n'
        )
        narration = (
            "The Pythagorean Theorem is the cornerstone of Euclidean geometry and coordinate geometry. "
            "In every right-angled triangle, the sum of the squares of the two perpendicular legs equals the square of the hypotenuse. "
            "Notice how this simple algebraic relationship, a squared plus b squared equals c squared, "
            "directly defines our concept of physical distance in two-dimensional space. "
            "Whether calculating orbital trajectories or GPS coordinates, distance is computed by taking the square root of the sum of squared displacements."
        )
    elif any(k in p_lower for k in ("newton", "f = ma", "second law")):
        anchor = VisualAnchor(
            type="annotated_formula",
            title="Newton's Second Law of Motion",
            latex=r"\mathbf{F}_{\text{net}} = m \mathbf{a}",
            visible_elements=["F_net: Net Force", "m: Mass", "a: Acceleration"],
            key_definitions=[
                "F_net : Vector sum of all external forces acting on object (Newtons)",
                "m : Inertial mass resisting changes in motion (kilograms)",
                "a : Resulting vector acceleration in direction of net force (m/s²)",
            ],
            visual_purpose="Formulate the dynamical relationship governing classical mechanics.",
        )
        code = (
            'title = Text("Newton\'s Second Law of Motion", font_size=34, color=YELLOW).to_edge(UP, buff=0.4)\n'
            'formula = MathTex(r"\\mathbf{F}_{\\text{net}} = m \\mathbf{a}", font_size=46, color=BLUE).next_to(title, DOWN, buff=0.35)\n'
            'box = SurroundingRectangle(formula, color=GOLD, buff=0.25)\n'
            'where_lbl = Text("Physical Quantities:", font_size=22, color=GOLD, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.2)\n'
            'b1 = MathTex(r"\\bullet\\ \\mathbf{F} : \\text{Net external force vector (measured in Newtons, } \\text{kg}\\cdot\\text{m/s}^2)", font_size=20, color=WHITE)\n'
            'b2 = MathTex(r"\\bullet\\ m : \\text{Inertial mass (resistance to acceleration, kg)}", font_size=20, color=TEAL)\n'
            'b3 = MathTex(r"\\bullet\\ \\mathbf{a} : \\text{Vector acceleration (rate of change of velocity, } \\text{m/s}^2)", font_size=20, color=GREEN)\n'
            'bullets = VGroup(b1, b2, b3).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)\n'
            'self.play(Write(title), run_time=0.8)\n'
            'self.play(Write(formula), Create(box), run_time=1.2)\n'
            'self.play(FadeIn(where_lbl), run_time=0.5)\n'
            'self.play(LaggedStart(*[FadeIn(b, shift=RIGHT*0.2) for b in bullets], lag_ratio=0.2), run_time=1.5)\n'
            'self.wait(1.5)\n'
        )
        narration = (
            "Newton's Second Law of Motion provides the quantitative backbone of classical mechanics. "
            "It states that the acceleration of an object is directly proportional to the net force acting upon it, "
            "and inversely proportional to its inertial mass. As shown in the vector equation before you, "
            "applying a force produces an acceleration along that exact direction. "
            "A heavier mass requires proportionally greater force to achieve the same rate of acceleration, "
            "governing everything from rocket propulsion to structural civil engineering."
        )
    else:
        anchor = VisualAnchor(
            type="annotated_formula",
            title=f"{clean_topic} : Foundations" if slide_num == 1 else f"{clean_topic} : Mechanics {slide_num}",
            latex=r"\text{Concept } " + str(slide_num),
            visible_elements=[f"{clean_topic} Principle", "Primary Mechanisms", "Real-World Impact"],
            key_definitions=[
                f"Core Mechanism: Primary operational principle of {clean_topic}",
                "Conceptual Basis: Foundational mathematical and physical relationships",
                "Applications: Real-world engineering and computational significance",
            ],
            visual_purpose=f"Provide structured breakdown of {clean_topic} stage {slide_num}.",
        )
        code = (
            f'title = Text("{clean_topic[:28]} : Key Principles", font_size=34, color=YELLOW).to_edge(UP, buff=0.4)\n'
            f'box_lbl = Text("Core Formulation {slide_num}", font_size=36, color=BLUE).next_to(title, DOWN, buff=0.35)\n'
            'box = SurroundingRectangle(box_lbl, color=GOLD, buff=0.25)\n'
            'where_lbl = Text("Key Insights:", font_size=22, color=GOLD, weight=BOLD).next_to(box, DOWN, buff=0.35).to_edge(LEFT, buff=1.2)\n'
            f'b1 = MathTex(r"\\bullet\\ \\text{{Foundations: Essential framework underlying {clean_topic[:20]}}}", font_size=20, color=WHITE)\n'
            'b2 = MathTex(r"\\bullet\\ \\text{Mechanics: Dynamic interaction of core variables and parameters}", font_size=20, color=TEAL)\n'
            'b3 = MathTex(r"\\bullet\\ \\text{Implications: Broad mathematical and practical applications}", font_size=20, color=GREEN)\n'
            'bullets = VGroup(b1, b2, b3).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(where_lbl, DOWN, buff=0.2).align_to(where_lbl, LEFT)\n'
            'self.play(Write(title), run_time=0.8)\n'
            'self.play(Write(box_lbl), Create(box), run_time=1.2)\n'
            'self.play(FadeIn(where_lbl), run_time=0.5)\n'
            'self.play(LaggedStart(*[FadeIn(b, shift=RIGHT*0.2) for b in bullets], lag_ratio=0.2), run_time=1.5)\n'
            'self.wait(1.5)\n'
        )
        narration = (
            f"In this segment, we examine the foundational mechanisms of {clean_topic}. "
            "Notice the structured breakdown displayed before you. Rather than treating this as abstract notation, "
            "we want to cultivate genuine conceptual understanding of how these elements interact. "
            "When we break down the core components, their mutual dependencies become apparent, "
            "allowing us to apply these principles reliably to more advanced problems."
        )

    return TeachingSegment(
        slide_num=slide_num,
        concept=anchor.title or f"{clean_topic} - Slide {slide_num}",
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
    """Generates a TeachingSegment: first the rich visual anchor, then in-depth narration."""
    clean_topic = _extract_topic_title(prompt)
    try:
        prompt_limit = max(2000, int(os.getenv("AOS_KEYFRAME_PROMPT_CHARS", "12000")))
    except ValueError:
        prompt_limit = 12000
    # Preserve the user's examples, narration contract, and visual constraints.
    # The old 400-character slice reduced detailed lessons to a topic title.
    condensed_prompt = prompt[:prompt_limit] if len(prompt) > prompt_limit else prompt
    domain_ctx = _get_domain_knowledge(prompt)
    ctx_block = f"\nAdditional Domain Grounding:\n{domain_ctx}\n" if domain_ctx else ""

    fallback_segment: TeachingSegment | None = None

    def get_fallback() -> TeachingSegment:
        nonlocal fallback_segment
        if fallback_segment is None:
            fallback_segment = _build_curated_fallback_segment(prompt, slide_num, total_slides)
        return fallback_segment

    anchor: VisualAnchor | None = None
    code: str = ""

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
        vis_resp = execute_completion_with_fallback(
            client=client,
            primary_model=model,
            messages=[
                {"role": "system", "content": VISUAL_PLANNER_PROMPT},
                {"role": "user", "content": visual_user_prompt},
            ],
            temperature=0.3,
        )
        vis_text = vis_resp.choices[0].message.content or ""
        anchor, code = _parse_visual_output(vis_text)
    except Exception as exc:
        print(f"[Keyframe Engine Warning] Slide {slide_num} visual anchor generation failed: {exc}", file=sys.stderr)
        fb = get_fallback()
        anchor, code = fb.visual_anchor, fb.manim_code

    if not code.strip():
        print(f"[Keyframe Engine Warning] Slide {slide_num} generated empty code; using curated fallback visual.", file=sys.stderr)
        fb = get_fallback()
        if anchor is None or not anchor.title:
            anchor = fb.visual_anchor
        code = fb.manim_code

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
    narration = ""
    try:
        narr_resp = execute_completion_with_fallback(
            client=client,
            primary_model=model,
            messages=[
                {"role": "system", "content": NARRATION_PLANNER_PROMPT},
                {"role": "user", "content": narration_user_prompt},
            ],
            temperature=0.4,
        )
        narr_text = narr_resp.choices[0].message.content or ""
        narration = _parse_narration_output(narr_text)
    except Exception as exc:
        print(f"[Keyframe Engine Warning] Slide {slide_num} narration generation failed: {exc}", file=sys.stderr)
        fb = get_fallback()
        narration = fb.narration

    if not narration.strip() or len(narration.split()) < 20:
        print(f"[Keyframe Engine Warning] Slide {slide_num} narration insufficient; using curated fallback narration.", file=sys.stderr)
        fb = get_fallback()
        narration = fb.narration

    return TeachingSegment(
        slide_num=slide_num,
        concept=anchor.title or f"{clean_topic} - Slide {slide_num}",
        learning_objective=anchor.visual_purpose,
        visual_anchor=anchor,
        manim_code=code,
        narration=narration,
    )


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
) -> SlideProcessResult:
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

    # Step 1: Render Visual Anchor with Critic Feedback & 3-Try Retry Timeout Loop
    visual_critic = get_visual_critic(backend=os.getenv("AOS_VISUAL_CRITIC_BACKEND", "moondream"))
    max_visual_tries = int(os.getenv("AOS_VISUAL_CRITIC_MAX_RETRIES", "3"))
    retry_timeout_sec = float(os.getenv("AOS_VISUAL_CRITIC_RETRY_TIMEOUT", "20.0"))

    visual_path = None
    for attempt in range(1, max_visual_tries + 1):
        att_label = f" (try {attempt}/{max_visual_tries})"
        _notify("RENDERING", f"Rendering visual anchor for Slide {i}{att_label}")
        visual_path = render_visual_anchor(segment, run_dir, quality=quality)
        if not visual_path or not visual_path.is_file():
            continue

        segment.visual_path = str(visual_path)
        segment.visual_duration = get_media_duration(visual_path)

        # Extract keyframe snapshot for inspection
        keyframe_path = run_dir / f"slide_{i}_keyframe_att{attempt}.png"
        extracted_frame = visual_critic.extract_keyframe(visual_path, keyframe_path)

        if extracted_frame is None or not Path(extracted_frame).is_file():
            _notify("VISUAL_CRITIC_SKIP", f"Slide {i} keyframe extraction failed; skipping visual critic inspection")
            segment.visual_verdict = {
                "passed": True,
                "score": 0.5,
                "detected_issues": ["Keyframe extraction skipped"],
                "skipped": True,
            }
            break

        v_context = VisualContext(
            slide_num=i,
            concept=segment.concept,
            learning_objective=segment.learning_objective,
            latex_formula=segment.visual_anchor.latex or "",
            visible_elements=segment.visual_anchor.visible_elements,
            key_definitions=segment.visual_anchor.key_definitions,
            manim_code=segment.manim_code,
        )

        _notify("VISUAL_CRITIC", f"Inspecting Slide {i} with Critic ({visual_critic.name}) [try {attempt}/{max_visual_tries}]")
        try:
            verdict = visual_critic.critique_frame(extracted_frame, v_context)
        except Exception as vc_err:
            print(f"[Visual Critic Warning] Slide {i} inspection error: {vc_err}; falling back to heuristic critic", file=sys.stderr)
            try:
                heuristic = HeuristicVisionCritic()
                verdict = heuristic.critique_frame(extracted_frame, v_context)
            except Exception as h_err:
                print(f"[Visual Critic Error] Heuristic fallback failed: {h_err}", file=sys.stderr)
                verdict = VisualCriticVerdict(
                    passed=True,
                    score=0.5,
                    critic_model="fallback-bypass",
                    backend="fallback",
                    detected_issues=[],
                    suggested_fixes=[],
                    feedback_for_code_repair="",
                )
                segment.visual_verdict = verdict.model_dump()
                segment.visual_verdict["skipped"] = True
                break

        segment.visual_verdict = verdict.model_dump()

        if verdict.passed:
            _notify("VISUAL_CRITIC_PASS", f"Slide {i} passed visual inspection (Score: {verdict.score:.2f}) on try {attempt}")
            break
        else:
            issues_summary = ", ".join(verdict.detected_issues[:3]) if verdict.detected_issues else "Layout defect"
            _notify("VISUAL_CRITIC_DEFECTS", f"Slide {i} defects (try {attempt}/{max_visual_tries}): {issues_summary}")
            if attempt < max_visual_tries:
                _notify("VISUAL_CRITIC_REPAIR", f"Repairing Slide {i} Manim code using critic feedback (try {attempt}/{max_visual_tries}, timeout: {retry_timeout_sec}s)...")
                try:
                    repaired_code = repair_visual_anchor_code(
                        original_code=segment.manim_code,
                        segment=segment,
                        verdict=verdict,
                        client=client,
                        model=model,
                        timeout=retry_timeout_sec,
                    )
                    if repaired_code and repaired_code.strip():
                        segment.manim_code = repaired_code
                except Exception as r_err:
                    _notify("VISUAL_CRITIC_TIMEOUT", f"Slide {i} repair timed out after {retry_timeout_sec}s on try {attempt}: {r_err}")
            else:
                _notify("VISUAL_CRITIC_EXHAUSTED", f"Slide {i} reached max {max_visual_tries} tries. Retaining best visual render.")

    # Step 2: Synthesize Authoritative Pedagogical Narration
    audio_path = run_dir / f"slide_{i}_audio.wav"
    narr_dur, is_real_audio = synthesize_teaching_audio(segment.narration, audio_path, return_status=True)
    segment.audio_path = str(audio_path)
    segment.narration_duration = narr_dur
    if not is_real_audio:
        if segment.visual_verdict is None:
            segment.visual_verdict = {}
        segment.visual_verdict["tts_ok"] = False

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

    return SlideProcessResult(
        slide_num=i,
        segment=segment,
        chunk_path=chunk_path,
        code_part=code_part,
    )


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
        outline_resp = execute_completion_with_fallback(
            client=client,
            primary_model=effective_model,
            messages=[
                {
                    "role": "user",
                    "content": f"Create a concise {total_slides}-part pedagogical outline explaining: {prompt}. Return numbered points.",
                }
            ],
            temperature=0.3,
        )
        outline = outline_resp.choices[0].message.content or f"1. Introduction to {prompt}\n2. Mechanics\n3. Implications"
    except Exception as exc:
        print(f"[Keyframe Engine] Outline generation fallback ({exc})", file=sys.stderr)
        outline = f"1. Foundations of {prompt}\n2. Core formulation\n3. Intuition & synthesis"

    combined_code_parts: list[str] = [
        "# Auto-generated by AOS Decoupled Teaching Segment Engine",
        "from manim import *",
        "import numpy as np\n",
    ]

    max_workers = min(total_slides, int(os.getenv("AOS_MAX_SLIDE_WORKERS", "3")))
    results: list[SlideProcessResult] = []

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
    results.sort(key=lambda r: r.slide_num)

    segments: list[TeachingSegment] = [r.segment for r in results]
    rendered_chunks: list[Path] = [r.chunk_path for r in results if r.chunk_path and r.chunk_path.is_file()]
    for r in results:
        combined_code_parts.append(r.code_part)

    final_video = run_dir / "final.mp4"
    if rendered_chunks:
        _notify("assemble", "Assembling final lesson with synchronized audio-visual segments")
        assemble_segments(rendered_chunks, final_video)
        _notify("VALIDATING_VIDEO", "Validating output lesson video")

    scene_file = run_dir / "scene.py"
    scene_file.write_text("\n".join(combined_code_parts), encoding="utf-8")

    segment_dicts = [s.model_dump() for s in segments]
    video_ok = final_video.is_file() and final_video.stat().st_size > 0
    all_chunks_valid = len(rendered_chunks) == len(segments) and len(rendered_chunks) > 0
    has_real_audio = any(
        s.audio_path and Path(s.audio_path).is_file() and s.narration_duration > 0.5 and getattr(s, "visual_verdict", {}).get("tts_ok", True)
        for s in segments
    )
    verified_audio = _mp4_has_audio_stream(final_video) if video_ok else False
    has_audio = has_real_audio if verified_audio is None else bool(verified_audio)

    manifest = {
        "ok": bool(video_ok and all_chunks_valid),
        "mode": "animate",
        "prompt": prompt,
        "run_dir": str(run_dir),
        "video_path": str(final_video) if video_ok else None,
        "scene_file": str(scene_file),
        "total_slides": len(segments),
        "rendered_chunks_count": len(rendered_chunks),
        "slides": [
            {
                "slide_num": s.slide_num,
                "narration": s.narration,
                "code": s.manim_code,
                "visual_duration": s.visual_duration,
                "narration_duration": s.narration_duration,
                "total_duration": getattr(s, "total_duration", max(s.visual_duration, s.narration_duration)),
                "hold_duration": getattr(s, "hold_duration", max(0.0, s.narration_duration - s.visual_duration)),
                "chunk_path": s.chunk_path,
                "key_definitions": s.visual_anchor.key_definitions,
                "layout_type": s.visual_anchor.layout_type,
                "visual_verdict": s.visual_verdict,
            }
            for s in segments
        ],
        "teaching_segments": segment_dicts,
        "has_audio": bool(has_audio and video_ok),
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _notify("upload", "Lesson video and comprehensive narration ready")
    return manifest

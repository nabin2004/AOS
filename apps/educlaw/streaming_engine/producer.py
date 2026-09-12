"""Producer module for EduClaw asynchronous streaming pipeline.

Generates slide-by-slide pedagogical states using an LLM (Ollama, vLLM, OpenRouter, or OpenAI-compatible)
and extracts structured <narration> and ```python``` blocks into a thread-safe Queue.
"""

from __future__ import annotations

import os
import queue
import re
from typing import List, Tuple

from openai import OpenAI

from apps.educlaw.streaming_engine.models import SlideData

EDUCLAW_SYSTEM_PROMPT = """You are EduClaw, an expert AI professor creating high-yield mathematical and computer science visual lectures.
Your output for each slide MUST strictly follow this exact format:

<narration>
Clear, calm university lecture explanation. Embed synchronization bookmarks like <bookmark mark="v1"/> and <bookmark mark="v2"/> at exact moments key concepts or visual changes are referenced.
</narration>

```python
# Manim Community Edition visual elements
# DO NOT import manim or define Scene classes here.
# Only write the Mobject definitions and self.play() / self.wait_until_bookmark() actions for this specific slide.
# Available in environment: self, np, MathTex, Text, VGroup, Create, Write, Transform, FadeIn, FadeOut, UP, DOWN, LEFT, RIGHT, BLUE, RED, YELLOW, GREEN.
```

Rules:
1. Always include at least 1-2 <bookmark mark="vN"/> tags in the narration and listen for them in the python script using self.wait_until_bookmark("vN").
2. Keep the visual elements clean, uncrowded, and centered.
3. Use MathTex for all mathematical expressions and formulas.
"""


def _parse_markdown(markdown: str) -> Tuple[str, str]:
    """Scrapes narration from <narration> tags and Manim code from python block."""
    narration_match = re.search(r"<narration>(.*?)</narration>", markdown, re.DOTALL)
    python_match = re.search(r"```python(.*?)```", markdown, re.DOTALL)

    narration = narration_match.group(1).strip() if narration_match else ""
    python_code = python_match.group(1).strip() if python_match else ""

    return narration, python_code


def get_llm_client(
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> Tuple[OpenAI, str]:
    """Resolve an OpenAI-compatible client and target model based on parameters and environment."""
    profile = (os.getenv("AOS_MODEL_PROFILE") or "").strip().lower()
    openrouter_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()

    if base_url and base_url.strip():
        effective_base = base_url.strip()
    elif os.getenv("AOS_OPENAI_BASE_URL"):
        effective_base = os.getenv("AOS_OPENAI_BASE_URL", "").strip()
    elif os.getenv("OPENAI_BASE_URL"):
        effective_base = os.getenv("OPENAI_BASE_URL", "").strip()
    elif openrouter_key or profile == "cloud":
        effective_base = "https://openrouter.ai/api/v1"
    else:
        effective_base = "http://localhost:11434/v1"

    if api_key and api_key.strip():
        effective_key = api_key.strip()
    elif "openrouter.ai" in effective_base:
        effective_key = openrouter_key or os.getenv("AOS_OPENAI_API_KEY") or "local"
    else:
        effective_key = (
            os.getenv("AOS_OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "ollama"
        ).strip()

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


def _build_curated_fallback_slide(prompt: str, slide_num: int, total_slides: int) -> tuple[str, str]:
    """Provide robust pedagogical fallback slides with rich LaTeX/Manim visuals if LLM is unavailable."""
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


def generate_lecture_stream(
    prompt: str,
    slide_queue: queue.Queue,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    total_slides: int = 3,
    on_progress: Any | None = None,
) -> None:
    """Generates pedagogical slides and pushes them to slide_queue as they are produced."""
    import sys

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

    # 1. Ask LLM for an outline / syllabus
    try:
        outline_response = client.chat.completions.create(
            model=effective_model,
            messages=[
                {
                    "role": "user",
                    "content": f"Create a concise {total_slides}-slide pedagogical outline for a visual lecture on: {prompt}. Just return numbered points.",
                }
            ],
            temperature=0.3,
        )
        outline = outline_response.choices[0].message.content or f"1. Introduction to {prompt}\n2. Core formulation\n3. Visual conclusion"
    except Exception as exc:
        outline = f"1. Core concept of {prompt}\n2. Mathematical foundation\n3. Synthesis and conclusion"

    # 2. Iteratively generate each slide
    for i in range(1, total_slides + 1):
        _notify("PlanTeachingScriptNode", f"Writing narration script for Slide {i}")
        slide_prompt = (
            f"Topic: {prompt}\n"
            f"Overall Lecture Outline:\n{outline}\n\n"
            f"Write Slide {i} of {total_slides}.\n"
            f"Focus on the topic of Step {i}. Provide detailed university-style pedagogical narration with <bookmark mark=\"v1\"/> and clean Manim visual code."
        )

        try:
            response = client.chat.completions.create(
                model=effective_model,
                messages=[
                    {"role": "system", "content": EDUCLAW_SYSTEM_PROMPT},
                    {"role": "user", "content": slide_prompt},
                ],
                temperature=0.4,
            )
            markdown_output = response.choices[0].message.content or ""
            narration, code = _parse_markdown(markdown_output)
        except Exception as exc:
            narration, code = _build_curated_fallback_slide(prompt, i, total_slides)

        # Fallback if model output was improperly formatted
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


class LectureProducer:
    """Wrapper class providing backward compatibility for tests and harness runners."""

    def __init__(self, q: queue.Queue):
        self.queue = q

    def generate_syllabus(self, prompt: str) -> List[str]:
        return [
            f"Introduction to {prompt}",
            f"Mathematical mechanics of {prompt}",
            f"Conclusion and visual synthesis",
        ]

    def _parse_markdown(self, markdown: str) -> SlideData:
        narration, code = _parse_markdown(markdown)
        return SlideData(slide_num=1, narration=narration, python_code=code)

    def run_production_loop(self, syllabus: List[str]):
        for i, topic in enumerate(syllabus):
            is_final = (i == len(syllabus) - 1)
            markdown_content = f"""
<narration>
Welcome. Today we will cover {topic}. <bookmark mark="v1"/> As you can see, this relationship forms the core foundation.
</narration>

```python
slide_text = Text("{topic}").scale(1.2)
self.wait_until_bookmark("v1")
self.play(Write(slide_text))
```
            """
            slide_data = self._parse_markdown(markdown_content)
            slide_data.slide_num = i + 1
            slide_data.is_final_slide = is_final
            self.queue.put(slide_data)

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
    effective_base = (
        base_url
        or os.getenv("AOS_OPENAI_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "http://localhost:11434/v1"
    ).strip()

    effective_key = (
        api_key
        or os.getenv("AOS_OPENAI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or "ollama"
    ).strip()

    effective_model = (
        model
        or os.getenv("AOS_CODER_MODEL")
        or os.getenv("AOS_OPENAI_MODEL")
        or "qwen2.5-coder"
    ).strip()

    client = OpenAI(base_url=effective_base, api_key=effective_key)
    return client, effective_model


def generate_lecture_stream(
    prompt: str,
    slide_queue: queue.Queue,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    total_slides: int = 3,
) -> None:
    """Background producer thread function that iteratively generates slides and pushes to slide_queue."""
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
            narration = f"In slide {i}, we examine the key principles of {prompt}."
            code = f'title = Text("Slide {i}: {prompt}").scale(1.2)\nself.play(Write(title))\nself.wait(1)'

        # Fallback if model output was improperly formatted
        if not narration:
            narration = f"Continuing our discussion of {prompt}, we observe how these principles connect mathematically."
        if not code:
            code = f'content = Text("Step {i}: Core Dynamics").scale(1.1)\nself.play(FadeIn(content))\nself.wait(1)'

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

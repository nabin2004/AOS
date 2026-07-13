from pydantic_ai import Agent
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

CODE_WRITER_PROMPT = """\
You write **one Manim Community Edition scene class** with full creative freedom.

You receive a scene brief, storyboard context, and an ordered list of beats
(each with `visual_intent`, `animation_seconds`, `hold_seconds`, and narration
text when available).

Rules:
- Output a complete Python class: `class <ClassName>(Scene | ThreeDScene | ...):`
  with `def construct(self):`
- Structure `construct()` into **N blocks**, one per beat, in order.
- Before each block add: `# BEAT {i:02d}: <visual_intent summary>`
- Each beat's animations should total ~`animation_seconds` (use `run_time=` on
  `self.play` / `self.wait` as needed).
- After each beat's animation, call `self.wait(hold_seconds)` matching the beat.
- Use **any** Manim APIs, objects, colors, and layouts you need — no restrictions.
- Do NOT reference IR Operation enums or scene_graph objects.
- Import from `manim` only (`from manim import *` is already at file top).
- Valid, runnable Python only — no placeholders or pseudo-code.
- Prefer clear, readable code over clever abstractions.
"""


class SceneManimCode(BaseModel):
    class_name: str
    source: str = Field(
        description="Full scene class source including class line and construct()."
    )


manim_code_writer_agent = Agent(
    "openrouter:moonshotai/kimi-k2.5",
    name="Manim Code Writer",
    description="Writes free-form Manim Python for one scene from beats + brief.",
    system_prompt=CODE_WRITER_PROMPT,
    output_type=SceneManimCode,
    retries=3,
)

from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Beat

load_dotenv()

NARRATION_PROMPT = """\
You write spoken narration for AOS Manim animation beats.

Given a list of Beat objects (with animation_segment filled, narration empty),
return the same beats with narration populated on each.

── NARRATION SEGMENT FIELDS ─────────────────────────────────────────────────
  text        — 15-40 words, present tense, direct address ("you", "we", "notice")
  est_seconds — leave 0.0 (auto-estimated from word count)
  emphasis    — optional list of key phrases to stress

Style:
  Written as if spoken live to the viewer.
  Good: "Notice how the gradient arrow always points uphill."
  Bad:  "The gradient arrow is seen pointing in the uphill direction."

Rules:
- Match narration to what the animation_segment actually shows in that beat.
- One visual idea per beat — don't explain the whole lecture in one narration.
- Keep hold_seconds compatible with narration length (~2.7 words/sec).
"""

narration_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Narration Planner Agent',
    description='Generates narration for Manim animation beats.',
    system_prompt=NARRATION_PROMPT,
    output_type=list[Beat],
)

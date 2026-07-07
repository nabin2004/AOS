from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import LectureIR

from tools import ToolDeps, aos_toolset

load_dotenv()

REPAIR_PROMPT = """\
You repair an AOS LectureIR document based on validation issues.

Given validation issues and the current partial or broken IR, return a corrected
full LectureIR document that fixes every listed issue.

Rules:
- Preserve the original pedagogical intent (lecture content and storyboard order).
- Fix reference integrity: every op target must exist in scene_graph before use.
- Respect cognitive load limits per beat.
- Ensure storyboard step.scene_id values match scene.id values.
- Fill in missing fields with sensible defaults (branding, render, opening, ending).
- Do not invent unrelated content — repair only what is broken or missing.
"""

repair_agent = Agent(
    'openrouter:openrouter/free',
    name='Repair Agent',
    description='Repairs the generated IR for correctness and completeness.',
    system_prompt=REPAIR_PROMPT,
    output_type=LectureIR,
    toolsets=[aos_toolset],
    deps_type=ToolDeps,
)

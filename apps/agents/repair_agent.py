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
- Ensure storyboard step.scene_id values match scene.id values.
- Fill in missing fields with sensible defaults (branding, render, opening, ending).
- Do not invent unrelated content — repair only what is broken or missing.

You only edit the IR document itself. You do not compile, render, or execute
anything — use validate_lecture_ir to check your fix before returning it.
"""

_REPAIR_TOOLS = {"validate_lecture_ir"}
repair_toolset = aos_toolset.filtered(lambda _ctx, tool_def: tool_def.name in _REPAIR_TOOLS)

repair_agent = Agent(
    'openrouter:openai/gpt-4o-mini',
    name='Repair Agent',
    description='Repairs the generated IR for correctness and completeness.',
    system_prompt=REPAIR_PROMPT,
    output_type=LectureIR,
    toolsets=[repair_toolset],
    deps_type=ToolDeps,
    retries=4,
)

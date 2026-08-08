from pydantic import BaseModel, Field
from pydantic_ai import Agent
from dotenv import load_dotenv
from llm_config import model_for_agent, settings_for

load_dotenv()


class InspectionResult(BaseModel):
    passed: bool
    summary: str
    issues: list[str] = Field(default_factory=list)


INSPECTOR_PROMPT = """\
You inspect AOS educational lecture animations after compile and Docker render.

The pipeline has already:
  - Compiled the LectureIR to lecture.py in the run workspace
  - Rendered each scene via Docker/Manim
  - Provided render success/failure and output paths in the prompt

Given the LectureIR JSON and render outcomes, evaluate whether the lecture is:
  - Pedagogically sound (correct teaching order, clear explanations)
  - Visually clear (not overcrowded, frame-safe positions, readable equations)
  - Narration-synced (narration matches what animation shows in each beat)
  - Technically rendered (note any scenes that failed to render)

Return:
  passed  — True if the lecture is ready to publish (all scenes rendered successfully)
  summary — 2-4 sentence overall assessment
  issues  — specific problems found (empty if passed)

You have no tools. Answer from the IR and render results in the prompt only.
"""

inspector_agent = Agent(
    model_for_agent("planner"),
    name='Inspector Agent',
    description='Inspects compiled Manim videos for correctness and completeness.',
    system_prompt=INSPECTOR_PROMPT,
    output_type=InspectionResult,
    model_settings=settings_for("planner"),
)

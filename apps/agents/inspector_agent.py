from pydantic import BaseModel, Field
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()


class InspectionResult(BaseModel):
    passed: bool
    summary: str
    issues: list[str] = Field(default_factory=list)


INSPECTOR_PROMPT = """\
You inspect compiled Manim educational videos for AOS.

Given a final LectureIR document, evaluate whether the rendered lecture would be:
  - Pedagogically sound (correct teaching order, clear explanations)
  - Visually clear (not overcrowded, frame-safe positions, readable equations)
  - Narration-synced (narration matches what animation shows in each beat)

Return:
  passed  — True if the lecture is ready to publish
  summary — 2-4 sentence overall assessment
  issues  — specific problems found (empty if passed)
"""

inspector_agent = Agent(
    'openrouter:openrouter/free',
    name='Inspector Agent',
    description='Inspects the compiled Manim videos for correctness and completeness.',
    system_prompt=INSPECTOR_PROMPT,
    output_type=InspectionResult,
)

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from dotenv import load_dotenv
from llm_config import model_for_agent, settings_for

load_dotenv()


class ValidationResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)


VALIDATION_PROMPT = """\
You validate an AOS LectureIR document for correctness and completeness.

Check these invariants (from the IR spec):

1. Storyboard ↔ scene linkage
   - Every storyboard step.scene_id exists in scenes.
   - No duplicate scene ids or class_names.

2. Structural completeness
   - lecture, storyboard, and scenes are present and consistent.
   - Beats have animation_segment; narration is filled where expected.
   - No duplicate scene object ids within a scene.

3. Obvious semantic issues (optional, non-blocking guidance)
   - Scene graphs should declare visual objects before beats animate them.
   - Beats should not be empty when narration is present.

Return:
  passed — True only when there are zero issues
  issues — list of specific, actionable problem descriptions (empty if passed)

Schema validation is run before you are invoked and has already passed. You are given
the JSON directly — inspect it for semantic issues only. You have no tools; answer from
the JSON in the prompt.
"""

validation_agent = Agent(
    model_for_agent("planner"),
    name='Validation Agent',
    description='Validates the generated IR for correctness and completeness.',
    system_prompt=VALIDATION_PROMPT,
    output_type=ValidationResult,
    model_settings=settings_for("planner"),
)

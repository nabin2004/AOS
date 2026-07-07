from pydantic import BaseModel, Field
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()


class ValidationResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)


VALIDATION_PROMPT = """\
You validate an AOS LectureIR document for correctness and completeness.

Check these invariants (from the IR spec):

1. Reference integrity
   - Every beat operation targets an id declared in the scene graph.
   - No duplicate scene object ids.
   - No ops on objects that haven't been created yet.
   - Camera ops target "__camera__" only.

2. Cognitive load (per beat)
   - ≤ 3 new objects introduced per beat
   - ≤ 1 new equation per beat
   - ≤ 2 simultaneously moving ops per beat
   - Narration length reasonable for hold_seconds

3. Storyboard ↔ scene linkage
   - Every storyboard step.scene_id exists in scenes.
   - No duplicate scene ids or class_names.

4. Structural completeness
   - lecture, storyboard, and scenes are present and consistent.
   - Beats have animation_segment; narration is filled where expected.

Return:
  passed — True only when there are zero issues
  issues — list of specific, actionable problem descriptions (empty if passed)
"""

validation_agent = Agent(
    'openrouter:openrouter/free',
    name='Validation Agent',
    description='Validates the generated IR for correctness and completeness.',
    system_prompt=VALIDATION_PROMPT,
    output_type=ValidationResult,
)

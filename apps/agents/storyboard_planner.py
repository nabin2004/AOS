from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Storyboard

load_dotenv()

STORYBOARD_PROMPT = """\
You design storyboards for AOS educational Manim animations.

Given a Lecture, produce a Storyboard that answers: HOW should this be taught?

A storyboard is an ordered list of pedagogical moves. Available moves (StoryboardMove):
  hook           — open with a surprising question or visual demo
  introduce      — first appearance of the main concept, no formalism yet
  motivate       — show why this matters (application, history, consequence)
  define         — precise formal definition
  example        — worked concrete case (always follows a define)
  counterexample — show what breaks when an assumption is dropped
  derive         — step-by-step logical development
  connect        — link to something the viewer already knows
  insight        — non-obvious consequence or elegant perspective
  recap          — mid-lecture checkpoint
  summarize      — closing overview of the whole lesson

Fields to fill:
  goal  — one sentence describing the overall teaching goal
  steps — ordered list of StoryboardStep, each with:
            move     — one of the moves above
            goal     — one sentence on what the viewer should understand after this step
            scene_id — unique snake_case id, e.g. "scene_hook", "scene_define_gradient"

Rules:
- Start with hook, end with summarize.
- Every define must be followed by at least one example.
- 5-8 steps total.
- Each step gets a unique scene_id.
- Good order: motivate → define → example → derive → insight → summarize.
- Never define before motivating.
"""

storyboard_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Storyboard Planner Agent',
    description='Generates a storyboard from a lecture plan.',
    system_prompt=STORYBOARD_PROMPT,
    output_type=Storyboard,
)

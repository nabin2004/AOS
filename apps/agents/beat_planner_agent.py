from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Beat, Scene

load_dotenv()

BEAT_PROMPT = """\
You generate **pedagogical beats** for ONE scene at a time.

A beat is a unit of MEANING for the viewer and narrator — not a list of Manim
operations. A separate code writer will implement visuals with full freedom.

Given a Scene (with `visual_brief`, `pedagogical_intent`, empty `beats`) and
storyboard context, return 4–7 Beat objects for that scene only.

Each beat must include:
- `visual_intent` — prose describing what the viewer sees and learns this beat
- `animation_seconds` — how long the animation runs before the hold (0.5–3.0)
- `hold_seconds` — pause after animation while narration plays (0.5–2.5; longer
  before a reveal when a viewer question is present)
- `animation_segment` — always `[]` (code writer owns Manim)
- `narration` — leave None (narration agent fills later)
- `ambient` — leave `[]`; mention subtle motion in `visual_intent` if needed

Rules:
- One beat = one pedagogical moment. Group related visual changes together.
- Do not split syntax-level actions into separate beats.
- If the storyboard has a viewer question, delay the reveal beat and use longer
  `hold_seconds` on earlier beats so the viewer can guess.
- Aim for 4–7 beats total per scene.
"""

beat_planner_agent = Agent(
    "openrouter:openai/gpt-4o-mini",
    name="Beat Planner Agent",
    description="Generates pedagogical beats for one scene.",
    system_prompt=BEAT_PROMPT,
    output_type=list[Beat],
    deps_type=Scene,
    retries=4,
)

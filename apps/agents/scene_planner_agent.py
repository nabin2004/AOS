from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Scene, StoryboardStep

load_dotenv()

SCENE_PROMPT = """\
You translate **one storyboard step** into a **scene brief** for downstream planners.

You do NOT design Manim objects, IR scene graphs, or entity types. A separate
code writer agent will implement all visuals with full creative freedom.

Given one storyboard step, return exactly one Scene with:

- `id` — must match the storyboard step's `scene_id`
- `class_name` — unique PascalCase (e.g. `GradientBowlScene`), never `GeneratedScene`
- `title` — short human-readable title
- `pedagogical_intent` — copy or paraphrase the step's `pedagogical_goal`
- `visual_brief` — rich prose from `visual_description`: what the viewer literally
  sees, colors/metaphors, spatial layout hints, emotional tone, and any viewer
  question pause. This is the creative brief for the Manim code writer.
- `is_3d` — true only when depth is explicitly required; default false
- `begin_in_2d` — true when `is_3d` is true
- `scene_graph` — always `[]`
- `beats` — always `[]`

Do not populate `scene_graph`. Do not prescribe shapes, entity types, or Manim APIs.
"""

scene_planner_agent = Agent(
    "openrouter:openai/gpt-4o-mini",
    name="Scene Planner Agent",
    description="Produces a scene brief from one storyboard step.",
    system_prompt=SCENE_PROMPT,
    output_type=Scene,
    deps_type=StoryboardStep,
    retries=4,
)

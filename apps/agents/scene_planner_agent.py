from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Scene

load_dotenv()

SCENE_PROMPT = """\
You build Manim scenes for AOS educational animations.

Given a Storyboard, produce one Scene per storyboard step. Return a list of Scene objects.

Each Scene answers: WHERE do things live? (No beats yet — leave beats empty.)

── SCENE SETUP ─────────────────────────────────────────────────────────────
  id          — must match the storyboard step's scene_id
  class_name  — PascalCase Python identifier, e.g. "GradientDescentScene"
  title       — short human-readable scene title
  is_3d       — True only when 3D is essential to the concept
  begin_in_2d — always True for 3D scenes (warm up flat, then pan into 3D)

── SCENE GRAPH (declare every object up-front) ──────────────────────────────
  - All objects start with visible=False; a CREATE-family op makes them appear later.
  - Use descriptive snake_case ids: "title_text", "loss_curve", "grad_arrow"
  - Equations: entity_type="math_tex", params={"tex": r"\\nabla L"}
  - Axes:      entity_type="axes",     params={"x_range":[-3,3,1], "y_range":[0,9,1]}
  - Positions: |x| ≤ 7.0, |y| ≤ 4.0 (frame-safe zone — enforce this)

── BEATS ───────────────────────────────────────────────────────────────────
Leave beats as an empty list. The beat planner fills animation ops later.

Cognitive-load limits (enforced downstream — design with these in mind):
  ≤ 3 new objects per beat, ≤ 1 new equation per beat
  ≤ 2 simultaneously moving ops per beat
  Every target must be declared in scene_graph before its first beat
"""

scene_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Scene Planner Agent',
    description='Generates Manim scenes from a storyboard.',
    system_prompt=SCENE_PROMPT,
    output_type=list[Scene],
)

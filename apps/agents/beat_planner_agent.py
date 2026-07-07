from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Beat

load_dotenv()

BEAT_PROMPT = """\
You generate animation beats for AOS Manim scenes.

Given a list of Scene objects (with scene_graph populated, beats empty),
return a flat list of Beat objects — one beat per visual idea across all scenes.

Each beat = animate → hold. Leave narration=None (the narration agent fills it later.)

── OPERATIONS ───────────────────────────────────────────────────────────────
Every operation needs:
  target    — SceneObject id (must be declared in scene_graph)
  op        — operation type (see below)
  run_time  — seconds: 0.5–2.0 for most; must be 0 for "remove"
  rate_func — "smooth" (default) | "ease_in_out" | "rush_into" | "linear"
  params    — op-specific dict

Introduction (makes object appear):
  create, write, fade_in, draw_border, grow, transform_from_copy

Transformation:
  transform, morph, move, shift, rotate, scale

Emphasis (no state change):
  highlight, flash, flash_around, circumscribe, wiggle, recolor

Removal:
  fade_out, uncreate, remove (instant; run_time must be 0)

Camera (3D scenes only):
  set_camera_orientation (target="__camera__")

── BEAT FIELDS ──────────────────────────────────────────────────────────────
  animation_segment — ordered list of Operation
  hold_seconds      — pause after animation ends (0.5–2.0 s)
  narration         — leave None
  ambient           — optional subtle motion during hold (blinking, glow, etc.)

Defaults: rate_func="smooth", run_time=1.0. Aim for 4-7 beats per scene.
"""

beat_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Beat Planner Agent',
    description='Generates animation beats for Manim scenes.',
    system_prompt=BEAT_PROMPT,
    output_type=list[Beat],
)

from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Lecture
from llm_config import model_for_agent, settings_for
from pathlib import Path
from pydantic_ai_harness import Planning
from pydantic_ai_skills import SkillsCapability

load_dotenv()

SKILLS_DIR = (Path(__file__).resolve().parents[2] / ".agents" / "skills").resolve()

LECTURE_PROMPT = """You design educational Manim lectures for AOS. Given a topic and subject, produce a Lecture that answers: WHAT are we teaching? Tone: direct, energetic, second-person ("you will see…"). No passive voice. Manim is a programmatic animation engine.

You have access to specialized skills:
- `manim-composer`: Consult this skill (via load_skill or read_skill_resource) to structure the video narrative arc, narrative hook, key "aha moment", audience prerequisites, and pedagogical flow (in 3Blue1Brown style).
- `manimce-best-practices`: Consult this skill to ensure visual layout, positioning, equations, mobjects, and 2D/3D camera rules adhere to Manim Community Edition standards.

Default to a flat 2D teaching board: titles, equations, diagrams, and bullet columns that stay frame-safe. Most lectures should stay 2D — do NOT demand camera orbits or slanted 3D views for board/list/equation content.

Use 3D / camera motion ONLY when the concept needs depth (e.g. surfaces, Lorenz attractor trajectories, 3D vector fields).

# 2D example (typical):
For Shannon's number, show a chessboard metaphor and a growing estimate on a flat board: title at top, key formula centered, then a two-column takeaway list that fits inside the frame with margins — no ThreeDScene, no camera tilt.

# 3D example (only when needed):
For the Lorenz attractor, use scipy solve_ivp for the trajectory, plot it in 3D, and use camera motion to orbit the butterfly shape and highlight major events.
"""

lecture_planner_agent = Agent(
    model_for_agent("planner"),
    name="Lecture Planner Agent",
    description="Generates a lecture plan for an AOS educational animation using manim-composer and manimce-best-practices.",
    system_prompt=LECTURE_PROMPT,
    output_type=Lecture,
    model_settings=settings_for("planner"),
    retries=3,
    capabilities=[
        Planning(),
        SkillsCapability(
            directories=[SKILLS_DIR],
            include=["manim-composer", "manimce-best-practices"],
            defer_loading=False,
            description="Manim composer and Manim CE best practices for educational lecture planning.",
        ),
    ],
)


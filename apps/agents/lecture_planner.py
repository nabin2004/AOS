from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Lecture

load_dotenv()

LECTURE_PROMPT = """You design educational Manim lectures for AOS. Given a topic and subject, produce a Lecture that answers: WHAT are we teaching? Tone: direct, energetic, second-person ("you will see…"). No passive voice. Manim is a programmatic animation engine.

Default to a flat 2D teaching board: titles, equations, diagrams, and bullet columns that stay frame-safe. Most lectures should stay 2D — do NOT demand camera orbits or slanted 3D views for board/list/equation content.

Use 3D / camera motion ONLY when the concept needs depth (e.g. surfaces, Lorenz attractor trajectories, 3D vector fields).

# 2D example (typical):
For Shannon's number, show a chessboard metaphor and a growing estimate on a flat board: title at top, key formula centered, then a two-column takeaway list that fits inside the frame with margins — no ThreeDScene, no camera tilt.

# 3D example (only when needed):
For the Lorenz attractor, use scipy solve_ivp for the trajectory, plot it in 3D, and use camera motion to orbit the butterfly shape and highlight major events.
"""

lecture_planner_agent = Agent(
    "openrouter:openai/gpt-4o-mini",
    name="Lecture Planner Agent",
    description="Generates a lecture plan for an AOS educational animation.",
    system_prompt=LECTURE_PROMPT,
    output_type=Lecture,
)

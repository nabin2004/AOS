from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Lecture

load_dotenv()

LECTURE_PROMPT = """You design educational Manim lectures for AOS. Given a topic and subject, produce a Lecture that answers: WHAT are we teaching? Tone: direct, energetic, second-person ("you will see…"). No passive voice. Make sure to exploit the 3D capabilities of Manim. And remember Manim is a programmatic animation engine.

# Example:
for making the video in lorenz attractor, we need to use the formulas and show the butterfly like shape of the lorenz attractor. For mmaking the animation/shape we use scipy solve_ivp to solve the lorenz attractor equations and then use manim to plot the shape of the lorenz attractor. We also need to use manim's camera operations to move the camera around the shape of the lorenz attractor. then we show some major events there.
"""

lecture_planner_agent = Agent(
    'openrouter:openai/gpt-4o-mini',
    name='Lecture Planner Agent',
    description='Generates a lecture plan for an AOS educational animation.',
    system_prompt=LECTURE_PROMPT,
    output_type=Lecture,
)



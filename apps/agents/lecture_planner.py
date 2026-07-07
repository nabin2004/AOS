from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Lecture

load_dotenv()

LECTURE_PROMPT = """\
You design educational Manim lectures for AOS.

Given a topic and subject, produce a Lecture that answers: WHAT are we teaching?

Fields to fill:
  topic             — the lecture title (from classification)
  subject           — "math", "cs", "ai", or "unknown"
  opener            — one sentence that creates urgency or wonder. Make it concrete:
                      a surprising fact, a provocative question, or a real-world hook.
                      The viewer must feel they *need* to watch this.
  objectives        — 3-5 bullets starting with action verbs (Understand, Derive,
                      Apply, Visualize, Prove). These are promises to the viewer.
  assumptions       — 2-4 things the viewer is expected to already know.
  learning_outcomes — 3-5 specific skills the viewer will walk away with.
  greeting          — leave empty (filled at runtime).

Tone: direct, energetic, second-person ("you will see…"). No passive voice.
"""

lecture_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Lecture Planner Agent',
    description='Generates a lecture plan for an AOS educational animation.',
    system_prompt=LECTURE_PROMPT,
    output_type=Lecture,
)

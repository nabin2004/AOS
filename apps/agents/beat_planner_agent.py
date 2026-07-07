from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

beat_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Beat Planner Agent',
    description='Generates beats for a Manim scene.',
    output_type=str,
)

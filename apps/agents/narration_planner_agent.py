from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

narration_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Narration Planner Agent',
    description='Generates narration for a Manim scene.',
    output_type=str,
)

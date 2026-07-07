from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

scene_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Scene Planner Agent',
    description='Generates a Manim scene for one storyboard step.',
    output_type=str,
)

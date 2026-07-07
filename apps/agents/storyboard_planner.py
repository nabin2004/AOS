from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

storyboard_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Storyboard Planner Agent',
    description='Generates a storyboard from a lecture plan.',
    output_type=str,
)

from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

lecture_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Lecture Planner Agent',
    description='Generates a lecture plan for an AOS educational animation.',
    output_type=str,
)

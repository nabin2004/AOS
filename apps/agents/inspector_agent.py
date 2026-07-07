from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

inspector_agent = Agent(
    'openrouter:openrouter/free',
    name='Inspector Agent',
    description='Inspects the compiled Manim videos for correctness and completeness.',
    output_type=str,
)

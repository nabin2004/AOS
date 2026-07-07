from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

repair_agent = Agent(
    'openrouter:openrouter/free',
    name='Repair Agent',
    description='Repairs the generated IR for correctness and completeness.',
    output_type=str,
)

from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

validation_agent = Agent(
    'openrouter:openrouter/free',
    name='Validation Agent',
    description='Validates the generated IR for correctness and completeness.',
    output_type=str,
)

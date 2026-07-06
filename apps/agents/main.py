import logfire
from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Classification

# logfire.configure()
# logfire.instrument_pydantic_ai()

# prompts
from .prompts import classification_instruction

load_dotenv()

agent = Agent(
    'openrouter:openrouter/free',
    system_prompt=classification_instruction,
    output_type=Classification,
    )

response = agent.run_sync("I want to learn about young's double slit experiment.")
print(response.output)
from pydantic_ai import Agent
from dotenv import load_dotenv

from ir.manim_ir import Subject

load_dotenv()

agent = Agent(
    'openrouter:openrouter/free',
    system_prompt="You are a helpful assistant who classifies the queries in subjects name.",
    output_type=Subject,
    )

response = agent.run_sync("I want to learn about young's double slit experiment.")
print(response.output)
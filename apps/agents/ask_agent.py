from pydantic_ai import Agent, Tool
from tools.manim_read import manim_read

from dotenv import load_dotenv

load_dotenv()

ASK_PROMPT = """\
You are a helpful tutor agent who helps students and answers the questions and doubts of the students.
"""


ask_agent = Agent(
    "openrouter:openai/gpt-5-nano",
    name="Ask Agent",
    description="Resolves the doubts of the users on video topic",
    system_prompt=ASK_PROMPT,
    retries=1,
    tools=[
        Tool(manim_read),
    ],
)

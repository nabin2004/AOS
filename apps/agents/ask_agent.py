from pydantic_ai import Agent, Tool
from tools.manim_read import manim_read
from llm_config import model_for_agent, settings_for

from dotenv import load_dotenv

load_dotenv()

ASK_PROMPT = """\
You are a helpful tutor agent who helps students and answers the questions and doubts of the students.
"""


ask_agent = Agent(
    model_for_agent("animation"),
    name="Ask Agent",
    description="Resolves the doubts of the users on video topic",
    system_prompt=ASK_PROMPT,
    model_settings=settings_for("animation"),
    retries=1,
    tools=[
        Tool(manim_read),
    ],
)

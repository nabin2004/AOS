from pydantic import BaseModel
from pydantic_ai import Agent
from dotenv import load_dotenv
from ir.manim_ir import Subject

load_dotenv()


class Classification(BaseModel):
    subject: Subject
    topic: str


CLASSIFICATION_PROMPT = """\
You are a subject classifier for AOS, an educational Manim lecture generator
covering Math, CS, and AI.

Given a user request, return:
  subject — the primary domain: "math", "cs", "ai", or "unknown"
  topic   — a clean 2-6 word, title-cased lecture title (no punctuation)

Domain guide:
  math — calculus, linear algebra, statistics, geometry, number theory, discrete math
  cs   — algorithms, data structures, complexity, systems, networking, programming
  ai   — machine learning, neural networks, optimization, NLP, computer vision, RL

Rules:
- Pick the single most specific domain.
- If the request spans two domains, use whichever the user's phrasing emphasizes.
- Topics completely outside Math/CS/AI (physics, biology, history) → "unknown".
- topic must read as a standard lecture title — no articles ("A", "The"), no trailing
  punctuation.
"""

classifier_agent = Agent(
    'openrouter:openrouter/free',
    name='Classifier Agent',
    description='Classifies a user request into a subject domain and topic name. If its out of domain, returns unknown.',
    system_prompt=CLASSIFICATION_PROMPT,
    output_type=Classification,
)

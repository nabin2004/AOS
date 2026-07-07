from pydantic_ai import Agent 
from dotenv import load_dotenv
from prompt_optimization.prompts.classification import Classification, CLASSIFICATION_PROMPT

load_dotenv()

classifier_agent = Agent(
    'openrouter:openrouter/free',
    name='Classifier Agent',
    description='Classifies a user request into a subject domain and topic name. If its out of domain, returns unknown.',
    system_prompt=CLASSIFICATION_PROMPT,
    output_type=Classification,
)
import logfire
from pydantic_ai import Agent
from dotenv import load_dotenv
# from apps.prompt_optimization.prompts import Classification, CLASSIFICATION_PROMPT

from prompt_optimization.prompts import Classification, CLASSIFICATION_PROMPT, LECTURE_PROMPT

# logfire.configure()
# logfire.instrument_pydantic_ai()

load_dotenv()

classifier_agent = Agent(
    'openrouter:openrouter/free',
    name='Classifier Agent',
    description='Classifies a user request into a subject domain and topic name. If its out of domain, returns unknown.',
    system_prompt=CLASSIFICATION_PROMPT,
    output_type=Classification,
)

lecture_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Lecture Planner Agent',
    description='Generates a lecture plan for an AOS educational animation.',
    system_prompt=LECTURE_PROMPT,
    output_type=,
)

storyboard_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Storyboard Planner Agent',
    description='Generates a storyboard from a lecture plan.',
    system_prompt=STORYBOARD_PROMPT,
    output_type=,
)

scene_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Scene Planner Agent',
    description='Generates a Manim scene for one storyboard step.',
    system_prompt=SCENE_PROMPT,
    output_type=,
)

beat_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Beat Planner Agent',
    description='Generates a Manim scene for one storyboard step.',
    system_prompt=BEAT_PROMPT,
    output_type=,
)

narration_planner_agent = Agent(
    'openrouter:openrouter/free',
    name='Narration Planner Agent',
    description='Generates a Manim scene for one storyboard step.',
    system_prompt=NARRATION_PROMPT,
    output_type=,
)

validation_agent = Agent(
    'openrouter:openrouter/free',
    name='Validation Agent',
    description='Validates the generated IR for correctness and completeness.',
    system_prompt=VALIDATION_PROMPT,
    output_type=,
)

repair_agent = Agent(
    'openrouter:openrouter/free',
    name='Repair Agent',
    description='Repairs the generated IR for correctness and completeness.',
    system_prompt=REPAIR_PROMPT,
    output_type=,
)

inspector_agent = Agent(
    'openrouter:openrouter/free',
    name='Inspector Agent',
    description='Inspects the compiled Manim videos for correctness and completeness.',
    system_prompt=INSPECTOR_PROMPT,
    output_type=,
)

response = classifier_agent.run_sync("I want to learn about young's double slit experiment.")
print(response.output)
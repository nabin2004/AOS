from typing import Any, Literal
from pydantic import BaseModel, Field
from rich.prompt import Prompt
from pydantic_ai import Agent, ModelMessage, RunContext, RunUsage, UsageLimits
from educlaw.animateworkflow import contracts
from contracts import RequestClassification
from educlaw.animateworkflow.prompts import RAW_CODE_PROMPT


from dotenv import load_dotenv

load_dotenv()  

requestAnalyser: Agent[object, RequestClassification] = Agent(
    model="openrouter:openai/gpt-4o-mini",
    name='RequestAnalyser',
    output_type=RequestClassification,
    instructions="You are a helpful assistant that classifies user requests for educational video content. "
)

# result = requestAnalyser.run_sync("Teach me about the Lorenz attractor?")

# print(result.output)  

generate_raw_code: Agent[object, contracts.LessonPlan] = Agent(
    model="openrouter:openai/gpt-4o-mini",
    name='generate_raw_code',
    output_type=contracts.LessonPlan,
    instructions=RAW_CODE_PROMPT
)


ScenePlannerAgent: Agent[object, str] = Agent(
    model="openrouter:openai/gpt-4o-mini",
    name='ScenePlannerAgent',
    # output_type='LessonPlan',
    instructions="You are a helpful assistant that plans the scenes needed to fulfill user requests for educational video content. "
)

NarrationPlannerAgent = Agent(
    model="openrouter:openai/gpt-4o-mini",    
    name='NarrationPlannerAgent',
    # output_type='NarrationPlan',
    instructions="You are a helpful assistant that plans the narration needed to fulfill user requests for educational video content. "
)

CodeGeneratorAgent = Agent(
    model="openrouter:openai/gpt-4o-mini",    
    name='CodeGeneratorAgent',
    instructions="You are a helpful assistant that generates code to fulfill user requests for educational video content. "
)

CompilerAgent = Agent(
    model="openrouter:openai/gpt-4o-mini",
    name='CompilerAgent',
    instructions="You are a helpful assistant that compiles code to fulfill user requests for educational video content. "
)

async def main():
    user_request = Prompt.ask("Enter your request for educational video content:")
    analysis_result = await requestAnalyser.run(user_request)
    classification = analysis_result.output
    print(f"[STEP-1] Request Classification: \n{classification}")

    raw_code_result = await generate_raw_code.run(user_request)
    raw_code: contracts.LessonPlan = raw_code_result.output
    print(f"[STEP-2] Raw Code Generated: \n{raw_code}")



import asyncio

asyncio.run(main())
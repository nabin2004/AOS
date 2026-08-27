from typing import Any, Literal
from pydantic import BaseModel, Field
from rich.prompt import Prompt
from pydantic_ai import Agent, AgentRunResult, ModelMessage, RunContext, RunUsage, UsageLimits
from educlaw.animateworkflow import contracts
from contracts import RequestClassification,NarrationPlan,FinalCode,CompileResult
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

# library_kb_agent: Agent[object, contracts.KnowledgeResult] = Agent(
#     model="openrouter:openai/gpt-4o-mini",
#     name='library_kb_agent',
#     output_type=contracts.KnowledgeResult,
#     instructions="You are a helpful assistant that provides knowledge about the educational content library. "
# )

NarrationPlannerAgent = Agent(
    model="openrouter:openai/gpt-4o-mini",    
    name='NarrationPlannerAgent',
    output_type=NarrationPlan,
    instructions="You are a helpful assistant that plans the narration needed to fulfill user requests for educational video content. "
)

CodeGeneratorAgent = Agent(
    model="openrouter:openai/gpt-4o-mini",    
    name='CodeGeneratorAgent',
    instructions="You are a helpful assistant that generates code to fulfill user requests for educational video content. ",
    output_type=FinalCode,
)

CompilerAgent: Agent[object, CompileResult] = Agent(
    model="openrouter:openai/gpt-4o-mini",
    name='CompilerAgent',
    instructions="You are a helpful assistant that compiles code to fulfill user requests for educational video content. ",
    output_type=CompileResult,

)

async def main():
    user_request = Prompt.ask("Enter your request for educational video content:")
    analysis_result = await requestAnalyser.run(user_request)
    classification = analysis_result.output
    print(f"[STEP-1] Request Classification: \n{classification}")

    raw_code_result = await generate_raw_code.run(user_request)
    raw_code: contracts.LessonPlan = raw_code_result.output
    print(f"[STEP-2] Raw Code Generated: \n{raw_code}")

    raw_code_prompt = raw_code.model_dump_json()
    scene_result, narration_result: tuple[AgentRunResult[str], AgentRunResult[str]] = await asyncio.gather(
        ScenePlannerAgent.run(raw_code_prompt),
        NarrationPlannerAgent.run(raw_code_prompt)
    )

    final_code_prompt = (
        f"Raw code plan:\n{raw_code_prompt}\n\n"
        f"Scene plan:\n{scene_result.output}\n\n"
        f"Narration plan:\n{narration_result.output}"
    )
    final_code: AgentRunResult[FinalCode] = await CodeGeneratorAgent.run(final_code_prompt)

    print(f"[STEP-3] Scene Planning Result: \n{scene_result.output}")
    print("="*50)
    print(f"[STEP-3] Narration Planning Result: \n{narration_result.output}")

    print("="*50)
    print(f"[STEP-4] Final Code Generation Result: \n{final_code.output}")


import asyncio

asyncio.run(main())
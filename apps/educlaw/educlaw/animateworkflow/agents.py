from pathlib import Path
from rich.prompt import Prompt
from pydantic_ai import Agent, AgentRunResult
from educlaw.animateworkflow import contracts
from .contracts import RequestClassification, NarrationPlan, FinalCode, LessonPlan
from educlaw.animateworkflow.prompts import NARRATION_PLANNER_INSTRUCTIONS, CODE_GENERATOR_INSTRUCTIONS
from educlaw.animateworkflow.compiler import compile_final_code
from dotenv import load_dotenv

load_dotenv()  

def build_agents() -> tuple[
    Agent[object, RequestClassification],
    Agent[object, contracts.LessonPlan],
    Agent[object, NarrationPlan],
    Agent[object, FinalCode],
]:
    model = "openrouter:openai/gpt-4o-mini"
    return (
        Agent(
            model=model,
            name="RequestAnalyser",
            output_type=RequestClassification,
            instructions="You are a helpful assistant that classifies user requests for educational video content.",
        ),
        Agent(
            model=model,
            name="ScenePlannerAgent",
            output_type=contracts.LessonPlan,
            instructions="You are a helpful assistant that plans the scenes needed to fulfill user requests for educational video content.",
        ),
        Agent(
            model=model,
            name="NarrationPlannerAgent",
            output_type=NarrationPlan,
            instructions=NARRATION_PLANNER_INSTRUCTIONS,
        ),
        Agent(
            model=model,
            name="CodeGeneratorAgent",
            instructions=CODE_GENERATOR_INSTRUCTIONS,
            output_type=FinalCode,
        ),
    )

async def main() :
    (
        requestAnalyser,
        ScenePlannerAgent,
        NarrationPlannerAgent,
        CodeGeneratorAgent,
    ) = build_agents()
    user_request = Prompt.ask("Enter your request for educational video content:")
    analysis_result = await requestAnalyser.run(user_request)
    print(analysis_result.output.video_id)
    classification = analysis_result.output
    print(f"[STEP-1] Request Classification: \n{classification}")

    scene_result: AgentRunResult[contracts.LessonPlan] = await ScenePlannerAgent.run(
        user_prompt=(
            f"Request:\n{user_request}\n\n"
            f"Classification:\n{classification.model_dump_json()}"
        )
    )
    lesson_plan = _normalize_lesson_plan(scene_result.output, classification)
    scene_plan_json = lesson_plan.model_dump_json()
    narration_prompt = (
        f"Request:\n{user_request}\n\n"
        f"Classification:\n{classification.model_dump_json()}\n\n"
        f"Lesson plan:\n{scene_plan_json}\n\n"
        f"Scene plan:\n{scene_plan_json}"
    )
    narration_result: AgentRunResult[NarrationPlan] = await NarrationPlannerAgent.run(
        user_prompt=narration_prompt
    )
    # scene_result, narration_result = results

    final_code_prompt = "\n\n".join(
        (
            f"Raw request:\n{user_request}",
            f"Raw analysis_result:\n{classification.model_dump_json()}",
            f"Raw code plan:\n{raw_code_prompt}",
            f"Scene plan:\n{scene_plan_json}",
            f"Narration plan:\n{narration_result.output.model_dump_json()}",
        )
    )
    final_code = await CodeGeneratorAgent.run(final_code_prompt)

    narration_result.output.validate_scene_ids(lesson_plan)
    print(f"[STEP-2] Scene Planning Result: \n{lesson_plan}")
    print("="*50)
    print(f"[STEP-3] Narration Planning Result: \n{narration_result.output}")

    print("="*50)
    print(f"[STEP-4] Final Code Generation Result: \n{final_code.output}")
    compile_result = compile_final_code(final_code.output, cwd=Path.cwd())
    print("="*50)
    print(f"[STEP-5] Compile Result: \n{compile_result}")


def _normalize_lesson_plan(plan: LessonPlan, classification: RequestClassification) -> LessonPlan:
    normalized = plan.model_copy(
        update={
            "videos": [
                video.model_copy(update={"video_id": classification.video_id})
                for video in plan.videos
            ]
        }
    )
    return normalized.validate_video_ids(classification.video_id)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
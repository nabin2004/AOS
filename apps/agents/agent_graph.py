from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage

from observability import configure_logfire, sft_batch_enabled

configure_logfire()

from coder_agent import SFT_BATCH_ADDENDUM, coder_agent
from coder_run import (
    CoderRunResult,
    arrange_coder_artifacts,
    new_coder_run_dir,
)
from classifier_agent import classifier_agent
from lecture_planner import lecture_planner_agent, Lecture
from ir.manim_ir import Subject, Classification
from dbos_setup import dbos_enabled, ensure_dbos_launched


def _run_classifier():
    if dbos_enabled():
        from durable_agents import durable_classifier

        return durable_classifier
    return classifier_agent


def _run_planner():
    if dbos_enabled():
        from durable_agents import durable_lecture_planner

        return durable_lecture_planner
    return lecture_planner_agent


def _run_coder():
    if dbos_enabled():
        from durable_agents import durable_coder

        return durable_coder
    return coder_agent


@dataclass
class AnimationState:
    user_query: str
    classification: Classification | None = None
    plan: Lecture | None = None
    code: str | None = None
    run_dir: str | None = None
    coder_result: CoderRunResult | None = None
    prompt_index: int | None = None


async def run_coder_step(
    topic: str,
    subject: str | Subject,
    plan: Lecture | str,
    *,
    usage: RunUsage | None = None,
    user_prompt: str | None = None,
    prompt_index: int | None = None,
) -> CoderRunResult:
    """Write/compile Manim for a topic; shared by the graph node and web tools."""
    if dbos_enabled():
        ensure_dbos_launched()

    run_dir = new_coder_run_dir(topic)

    prompt = (
        f"Topic: {topic}\n"
        f"Subject: {subject}\n"
        f"output_dir: {run_dir}\n"
        f"Use output_dir={run_dir!s} for every manim_write / compile_manim_code / "
        f"manim_read / synthesize_narration call.\n\n"
        f"Plan:\n{plan}"
    )
    if sft_batch_enabled():
        prompt += SFT_BATCH_ADDENDUM

    messages = None
    run_usage = usage
    summary = ""
    stopped_reason = "completed"

    try:
        result = await _run_coder().run(
            prompt,
            usage=usage,
        )
        messages = result.all_messages()
        run_usage = result.usage
        summary = str(result.output) if result.output is not None else ""
    except UsageLimitExceeded as exc:
        stopped_reason = f"usage_limit: {exc}"
        summary = stopped_reason

    return arrange_coder_artifacts(
        run_dir,
        messages=messages,
        usage=run_usage,
        summary=summary,
        stopped_reason=stopped_reason,
        request_limit=None,
        tool_calls_limit=None,
        user_prompt=user_prompt or topic,
        prompt_index=prompt_index,
    )


@dataclass
class ClassifyNode(BaseNode[AnimationState, None, str]):
    async def run(
        self, ctx: GraphRunContext[AnimationState]
    ) -> "PlanLectureNode | End[str]":
        if dbos_enabled():
            ensure_dbos_launched()
        result = await _run_classifier().run(ctx.state.user_query)
        ctx.state.classification = result.output

        if (
            ctx.state.classification is None
            or ctx.state.classification.subject == Subject.UNKNOWN
        ):
            return End("Domain not supported or classification failed.")

        return PlanLectureNode()


@dataclass
class PlanLectureNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "CodeAgent":
        if dbos_enabled():
            ensure_dbos_launched()
        result = await _run_planner().run(
            f"Topic: {ctx.state.classification.topic}\n"
            f"Subject: {ctx.state.classification.subject}"
        )
        ctx.state.plan = result.output
        return CodeAgent()


@dataclass
class CodeAgent(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> End[str]:
        coder_result = await run_coder_step(
            ctx.state.classification.topic,
            ctx.state.classification.subject,
            ctx.state.plan,
            user_prompt=ctx.state.user_query,
            prompt_index=ctx.state.prompt_index,
        )
        ctx.state.run_dir = coder_result.run_dir
        ctx.state.coder_result = coder_result
        ctx.state.code = coder_result.code

        end_summary = (
            f"stopped={coder_result.stopped_reason} "
            f"compile_ok={coder_result.compile_ok} "
            f"scene={coder_result.scene_name} "
            f"run_dir={coder_result.run_dir} "
            f"audio={len(coder_result.audio_paths)}"
        )
        return End(end_summary)


g = GraphBuilder(
    state_type=AnimationState, output_type=str, name="Manim Animation Graph"
)


@g.step
async def start(state: AnimationState) -> ClassifyNode:
    return ClassifyNode()


g.add(
    g.node(ClassifyNode),
    g.node(PlanLectureNode),
    g.node(CodeAgent),
    g.edge_from(g.start_node).to(start),
)

animation_graph = g.build()

import asyncio


async def run_pipeline(
    user_query: str,
    *,
    prompt_index: int | None = None,
) -> dict:
    if dbos_enabled():
        ensure_dbos_launched()
    state = AnimationState(user_query=user_query, prompt_index=prompt_index)
    summary = await animation_graph.run(state=state)
    if state.coder_result is not None:
        result = state.coder_result.model_dump(mode="json")
        if prompt_index is not None:
            result["prompt_index"] = prompt_index
        return result
    return {
        "result": summary,
        "stopped_reason": "classification_failed_or_unsupported",
    }


animation_agent = Agent(
    "openrouter:moonshotai/kimi-k2.5",
    name="Manim Animation Pipeline",
    description="Runs classify → lecture plan → Manim code/compile for a learning topic.",
    system_prompt=(
        "You run the Manim animation pipeline for educational topics.\n"
        "Act immediately — do not write long reasoning or preambles.\n"
        "Call tools in this exact order:\n"
        "1. classify_topic with the user's exact message\n"
        "2. plan_lecture with the returned topic and subject "
        "(skip if subject is unknown / unsupported — tell the user and stop)\n"
        "3. write_manim_animation with topic, subject, and the lecture plan\n"
        "Between tools, at most one short status line "
        "(e.g. 'Classifying…', 'Planning…', 'Writing Manim…').\n"
        "After write_manim_animation, summarize only from the tool result: "
        "stopped_reason, compile_ok, scene_name, run_dir, audio count. "
        "Do not invent paths or invent success if the tool reported failure."
    ),
)


@animation_agent.tool
async def classify_topic(ctx: RunContext, user_query: str) -> dict:
    """Classify the user request into a subject domain and lecture topic."""
    result = await classifier_agent.run(user_query, usage=ctx.usage)
    classification = result.output
    if classification is None:
        return {
            "ok": False,
            "supported": False,
            "subject": "unknown",
            "topic": None,
            "message": "Classification failed.",
        }
    supported = classification.subject != Subject.UNKNOWN
    payload = classification.model_dump(mode="json")
    payload["ok"] = True
    payload["supported"] = supported
    if not supported:
        payload["message"] = "Domain not supported (outside Math/CS/AI)."
    return payload


@animation_agent.tool
async def plan_lecture(ctx: RunContext, topic: str, subject: str) -> dict:
    """Generate a lecture plan for the classified topic."""
    result = await lecture_planner_agent.run(
        f"Topic: {topic}\nSubject: {subject}",
        usage=ctx.usage,
    )
    plan = result.output
    if plan is None:
        return {"ok": False, "message": "Lecture planning failed."}
    if hasattr(plan, "model_dump"):
        return {"ok": True, "plan": plan.model_dump(mode="json")}
    return {"ok": True, "plan": str(plan)}


@animation_agent.tool
async def write_manim_animation(
    ctx: RunContext,
    topic: str,
    subject: str,
    plan: str,
) -> dict:
    """Write, compile, and optionally narrate Manim code from the lecture plan."""
    coder_result = await run_coder_step(topic, subject, plan, usage=ctx.usage)
    return coder_result.model_dump(mode="json")


if __name__ == "__main__":
    result = asyncio.run(run_pipeline("I want to learn about Hairy Ball theorem."))
    print(result)

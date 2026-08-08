from dataclasses import dataclass
import json
import sys
from dotenv import load_dotenv

load_dotenv()

from pydantic_graph import BaseNode, End, EndMarker, GraphBuilder, GraphRunContext
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage

from observability import configure_logfire, sft_batch_enabled
from llm_config import is_ollama, model_for, model_for_agent, settings_for
from coder_prompt import (
    LOCAL_CODER_CODEMODE_HINT,
    compact_plan_for_local_coder,
    plan_to_payload,
)

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
class PipelineDeps:
    topic: str | None = None
    subject: str | None = None
    lecture_plan: dict | None = None


# pai web (and other callers) often run the agent without deps=PipelineDeps().
# Keep pipeline state in a module store reset at classify_topic.
_pipeline_state = PipelineDeps()


def _reset_pipeline_state() -> PipelineDeps:
    global _pipeline_state
    _pipeline_state = PipelineDeps()
    return _pipeline_state


def _pipeline_state_for(ctx: RunContext[PipelineDeps]) -> PipelineDeps:
    if ctx.deps is not None:
        return ctx.deps
    return _pipeline_state


@dataclass
class AnimationState:
    user_query: str
    classification: Classification | None = None
    plan: Lecture | None = None
    code: str | None = None
    run_dir: str | None = None
    coder_result: CoderRunResult | None = None
    prompt_index: int | None = None


def _subject_str(subject: str | Subject) -> str:
    if isinstance(subject, Subject):
        return subject.value
    return str(subject)


async def run_coder_step(
    topic: str,
    subject: str | Subject,
    plan: Lecture | str | dict,
    *,
    usage: RunUsage | None = None,
    user_prompt: str | None = None,
    prompt_index: int | None = None,
) -> CoderRunResult:
    """Write/compile Manim for a topic; shared by the graph node and web tools."""
    if dbos_enabled():
        ensure_dbos_launched()

    run_dir = new_coder_run_dir(topic)

    payload = plan_to_payload(plan)
    if is_ollama(model_for("coder")):
        payload = compact_plan_for_local_coder(payload)
    plan_text = json.dumps(payload, indent=2)

    codemode_hint = LOCAL_CODER_CODEMODE_HINT if is_ollama(model_for("coder")) else ""

    prompt = (
        f"Topic: {topic}\n"
        f"Subject: {_subject_str(subject)}\n"
        f"output_dir: {run_dir}\n"
        f"Use output_dir={run_dir!s} for every manim_write / compile_manim_code / "
        f"manim_read / synthesize_narration call.\n"
        f"{codemode_hint}\n"
        f"Plan:\n{plan_text}"
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
    except Exception as exc:
        stopped_reason = f"error: {exc}"
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
    # Prefer iter so UI/Celery can stream ``-> {node_id}`` on stderr.
    summary = ""
    async with animation_graph.iter(state=state) as run:
        async for step in run:
            if isinstance(step, EndMarker):
                summary = step.value if isinstance(step.value, str) else ""
                break
            for task in step:
                print(f"-> {task.node_id}", file=sys.stderr, flush=True)
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
    model_for_agent("animation"),
    deps_type=PipelineDeps,
    name="Manim Animation Pipeline",
    description="Runs classify → lecture plan → Manim code/compile for a learning topic.",
    model_settings=settings_for("animation"),
    system_prompt=(
        "You run the Manim animation pipeline for educational topics.\n"
        "Act immediately — do not write long reasoning or preambles.\n"
        "Call tools in this exact order:\n"
        "1. classify_topic with the user's exact message\n"
        "2. plan_lecture with the returned topic and subject "
        "(skip if subject is unknown / unsupported — tell the user and stop)\n"
        "3. write_manim_animation with topic and subject only "
        "(the lecture plan is stored automatically — do not pass plan text)\n"
        "Between tools, at most one short status line "
        "(e.g. 'Classifying…', 'Planning…', 'Writing Manim…').\n"
        "After write_manim_animation, summarize only from the tool result: "
        "stopped_reason, compile_ok, scene_name, run_dir, audio count. "
        "Do not invent paths or invent success if the tool reported failure."
    ),
)


@animation_agent.tool
async def classify_topic(ctx: RunContext[PipelineDeps], user_query: str) -> dict:
    """Classify the user request into a subject domain and lecture topic."""
    _reset_pipeline_state()
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
async def plan_lecture(ctx: RunContext[PipelineDeps], topic: str, subject: str) -> dict:
    """Generate a lecture plan for the classified topic."""
    result = await lecture_planner_agent.run(
        f"Topic: {topic}\nSubject: {subject}",
        usage=ctx.usage,
    )
    plan = result.output
    if plan is None:
        return {"ok": False, "message": "Lecture planning failed."}
    if hasattr(plan, "model_dump"):
        plan_payload = plan.model_dump(mode="json")
    else:
        plan_payload = {"raw": str(plan)}
    state = _pipeline_state_for(ctx)
    state.topic = topic
    state.subject = subject
    state.lecture_plan = plan_payload
    return {"ok": True, "plan": plan_payload}


@animation_agent.tool
async def write_manim_animation(
    ctx: RunContext[PipelineDeps],
    topic: str,
    subject: str,
) -> dict:
    """Write, compile, and optionally narrate Manim code from the stored lecture plan."""
    state = _pipeline_state_for(ctx)
    if state.lecture_plan is None:
        return {
            "ok": False,
            "stopped_reason": "no_plan",
            "message": "No lecture plan stored — call plan_lecture first.",
        }
    coder_result = await run_coder_step(
        topic,
        subject,
        state.lecture_plan,
        usage=ctx.usage,
    )
    return coder_result.model_dump(mode="json")


if __name__ == "__main__":
    prompt = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "I want to learn about Hairy Ball theorem."
    )
    result = asyncio.run(run_pipeline(prompt))
    print(result)

from dataclasses import dataclass
import sys
from dotenv import load_dotenv

load_dotenv()

from pydantic_graph import BaseNode, End, EndMarker, GraphBuilder, GraphRunContext
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage

from observability import configure_logfire, sft_batch_enabled
from llm_config import is_ollama, model_for, model_for_agent, settings_for, model_for_agent, settings_for
from openai_compatible import format_custom_endpoint_error
from coder_prompt import (
    build_coder_user_prompt,
    plan_to_payload,
)

configure_logfire()

from coder_agent import SFT_BATCH_ADDENDUM, coder_agent
from coder_run import (
    CoderRunResult,
    arrange_coder_artifacts,
    new_coder_run_dir,
)
from tools.coder_workspace import load_manifest
from tools.manim_source import extract_codemode_dump
from classifier_agent import classifier_agent
from lecture_planner import lecture_planner_agent, Lecture
from teaching_script import (
    TeachingScript,
    teaching_script_agent,
    teaching_script_to_payload,
    teaching_script_user_prompt,
)
from ir.manim_ir import Subject, Classification
from dbos_setup import dbos_enabled, ensure_dbos_launched


def _heuristic_classification(user_query: str) -> Classification | None:
    """In-domain fallback when the classifier model cannot emit structured output."""
    q = user_query.lower()
    math_hints = (
        "bodmas",
        "pemdas",
        "bidmas",
        "order of operations",
        "algebra",
        "calculus",
        "geometry",
        "trigonometry",
        "fraction",
        "equation",
        "matrix",
        "derivative",
        "integral",
        "probability",
        "statistics",
        "pythagoras",
        "quadratic",
        "arithmetic",
        "math",
        "euler",
        "e^{i",
        "complex number",
        "complex numbers",
        "cis",
        "unit circle",
        "formula",
        "theorem",
        "identity",
        "fourier",
        "de moivre",
    )
    cs_hints = (
        "algorithm",
        "data structure",
        "binary tree",
        "linked list",
        "complexity",
        "sorting",
        "recursion",
        "programming",
    )
    ai_hints = (
        "neural network",
        "machine learning",
        "gradient descent",
        "backpropagation",
        "transformer",
        "llm",
    )
    if any(h in q for h in math_hints):
        topic = "Math Topic"
        if "bodmas" in q:
            topic = "BODMAS"
        elif "pemdas" in q:
            topic = "PEMDAS"
        elif "euler" in q:
            topic = "Eulers Formula"
        return Classification(subject=Subject.MATH, topic=topic)
    if any(h in q for h in cs_hints):
        return Classification(subject=Subject.CS, topic="Computer Science Topic")
    if any(h in q for h in ai_hints):
        return Classification(subject=Subject.AI, topic="AI Topic")
    return None


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


def _run_teaching_script():
    if dbos_enabled():
        from durable_agents import durable_teaching_script

        return durable_teaching_script
    return teaching_script_agent


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
    teaching_script: dict | None = None


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
    teaching_script: TeachingScript | None = None
    code: str | None = None
    run_dir: str | None = None
    coder_result: CoderRunResult | None = None
    prompt_index: int | None = None


def _subject_str(subject: str | Subject) -> str:
    if isinstance(subject, Subject):
        return subject.value
    return str(subject)


def _assistant_text_from_messages(messages: list | None) -> str:
    if not messages:
        return ""
    chunks: list[str] = []
    for msg in messages:
        if getattr(msg, "kind", None) not in (None, "response"):
            continue
        for part in getattr(msg, "parts", None) or []:
            content = getattr(part, "content", None)
            if not isinstance(content, str) or not content.strip():
                continue
            part_kind = getattr(part, "part_kind", None)
            if part_kind in (None, "text"):
                chunks.append(content)
    return "\n".join(chunks)


def _salvage_codemode_text_dump(
    run_dir,
    *,
    summary: str,
    messages: list | None,
) -> None:
    """If the model dumped run_code as chat text, write+compile without eval."""
    manifest = load_manifest(run_dir)
    if manifest.get("scene_file") or (manifest.get("last_write") or {}).get("ok"):
        return

    blob = summary or ""
    extracted = extract_codemode_dump(blob)
    if extracted is None:
        extracted = extract_codemode_dump(_assistant_text_from_messages(messages))
    if extracted is None:
        return

    from tools.compile import compile_manim_code
    from tools.manim_write import manim_write

    manim_write(
        code=extracted.code,
        scene_name=extracted.scene_name,
        output_dir=str(run_dir),
    )
    compile_manim_code(
        code=extracted.code,
        scene_name=extracted.scene_name,
        output_dir=str(run_dir),
    )


async def run_coder_step(
    topic: str,
    subject: str | Subject,
    plan: Lecture | str | dict,
    *,
    teaching_script: TeachingScript | dict | None = None,
    usage: RunUsage | None = None,
    user_prompt: str | None = None,
    prompt_index: int | None = None,
) -> CoderRunResult:
    """Write/compile Manim for a topic; shared by the graph node and web tools."""
    if dbos_enabled():
        ensure_dbos_launched()

    run_dir = new_coder_run_dir(topic)

    payload = plan_to_payload(plan)
    script_payload = teaching_script_to_payload(teaching_script)
    if script_payload:
        payload["teaching_script"] = script_payload
    local_coder = is_ollama(model_for("coder"))
    prompt = build_coder_user_prompt(
        topic=topic,
        subject=_subject_str(subject),
        output_dir=run_dir,
        plan_payload=payload,
        compact=local_coder,
        include_codemode_hint=local_coder,
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
        stopped_reason = format_custom_endpoint_error(f"error: {exc}")
        summary = stopped_reason

    _salvage_codemode_text_dump(run_dir, summary=summary, messages=messages)

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
        classify_error: str | None = None
        try:
            result = await _run_classifier().run(ctx.state.user_query)
            ctx.state.classification = result.output
        except Exception as exc:
            classify_error = format_custom_endpoint_error(str(exc))
            print(f"classifier error: {classify_error}", file=sys.stderr, flush=True)
            ctx.state.classification = None

        if (
            ctx.state.classification is None
            or ctx.state.classification.subject == Subject.UNKNOWN
        ):
            fallback = _heuristic_classification(ctx.state.user_query)
            if fallback is not None:
                print(
                    f"-> ClassifyFallback {fallback.subject} {fallback.topic}",
                    file=sys.stderr,
                    flush=True,
                )
                ctx.state.classification = fallback
            else:
                detail = "Domain not supported or classification failed."
                if classify_error:
                    detail = f"{detail} ({classify_error[:400]})"
                return End(detail)

        return PlanLectureNode()


@dataclass
class PlanLectureNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "PlanTeachingScriptNode":
        if dbos_enabled():
            ensure_dbos_launched()
        try:
            result = await _run_planner().run(
                f"Topic: {ctx.state.classification.topic}\n"
                f"Subject: {ctx.state.classification.subject}"
            )
        except Exception as exc:
            raise RuntimeError(format_custom_endpoint_error(str(exc))) from exc
        ctx.state.plan = result.output
        return PlanTeachingScriptNode()


@dataclass
class PlanTeachingScriptNode(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> "CodeAgent":
        if dbos_enabled():
            ensure_dbos_launched()
        classification = ctx.state.classification
        plan = ctx.state.plan
        if classification is None or plan is None:
            return CodeAgent()
        try:
            result = await _run_teaching_script().run(
                teaching_script_user_prompt(
                    classification.topic,
                    _subject_str(classification.subject),
                    plan,
                )
            )
            ctx.state.teaching_script = result.output
        except Exception as exc:
            print(
                f"teaching script error: {format_custom_endpoint_error(str(exc))}",
                file=sys.stderr,
                flush=True,
            )
            ctx.state.teaching_script = None
        return CodeAgent()


@dataclass
class CodeAgent(BaseNode[AnimationState, None, str]):
    async def run(self, ctx: GraphRunContext[AnimationState]) -> End[str]:
        coder_result = await run_coder_step(
            ctx.state.classification.topic,
            ctx.state.classification.subject,
            ctx.state.plan,
            teaching_script=ctx.state.teaching_script,
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
    g.node(PlanTeachingScriptNode),
    g.node(CodeAgent),
    g.edge_from(g.start_node).to(start),
)

animation_graph = g.build()

import asyncio


def _find_compiled_video(run_dir: str | None) -> Path | None:
    if not run_dir:
        return None
    root = Path(run_dir)
    if not root.is_dir():
        return None
    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        try:
            import json
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            last = manifest.get("last_compile") or {}
            candidate = last.get("video_path") or manifest.get("video_path")
            if candidate and Path(candidate).is_file():
                return Path(candidate)
        except Exception:
            pass
    for path in root.rglob("*.mp4"):
        if path.is_file() and "partial_movie_files" not in path.parts:
            return path
    return None


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
    try:
        async with animation_graph.iter(state=state) as run:
            async for step in run:
                if isinstance(step, EndMarker):
                    summary = step.value if isinstance(step.value, str) else ""
                    break
                for task in step:
                    print(f"-> {task.node_id}", file=sys.stderr, flush=True)
    except Exception as exc:
        raise RuntimeError(format_custom_endpoint_error(str(exc))) from exc
    if state.coder_result is not None:
        result = state.coder_result.model_dump(mode="json")
        if prompt_index is not None:
            result["prompt_index"] = prompt_index

        import os
        if os.getenv("S3_VIDEO_ENDPOINT"):
            try:
                import uuid
                from tools.minio_storage import upload_to_minio
                video_path = _find_compiled_video(state.coder_result.run_dir)
                if video_path and video_path.is_file():
                    gen_id = uuid.uuid4()
                    video_key = f"videos/pipeline/{gen_id}.mp4"
                    code_key = f"videos/pipeline/{gen_id}.py"

                    video_url = upload_to_minio(video_path, object_key=video_key, content_type="video/mp4")
                    result["minio_url"] = video_url
                    result["minio_key"] = video_key
                    print(f"[minio] Uploaded video to {video_url}", file=sys.stderr, flush=True)

                    if state.coder_result.scene_file:
                        scene_path = Path(state.coder_result.run_dir) / state.coder_result.scene_file
                        if scene_path.is_file():
                            code_url = upload_to_minio(scene_path, object_key=code_key, content_type="text/x-python")
                            result["code_minio_url"] = code_url
                            result["code_minio_key"] = code_key
                            print(f"[minio] Uploaded scene code to {code_url}", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[minio] Upload failed: {e}", file=sys.stderr, flush=True)

        return result
    return {
        "result": summary,
        "stopped_reason": "classification_failed_or_unsupported",
        "error": summary or "classification_failed_or_unsupported",
        "message": summary or "Domain not supported or classification failed.",
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
        "(the lecture plan and teaching script are stored automatically — "
        "do not pass plan text)\n"
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
    """Generate a lecture plan and teaching script for the classified topic."""
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
    script_payload = None
    try:
        script_result = await teaching_script_agent.run(
            teaching_script_user_prompt(topic, subject, plan_payload),
            usage=ctx.usage,
        )
        script_payload = teaching_script_to_payload(script_result.output)
        state.teaching_script = script_payload
    except Exception as exc:
        print(
            f"teaching script error: {format_custom_endpoint_error(str(exc))}",
            file=sys.stderr,
            flush=True,
        )
        state.teaching_script = None
    return {"ok": True, "plan": plan_payload, "teaching_script": script_payload}


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
    if state.teaching_script is None:
        try:
            script_result = await teaching_script_agent.run(
                teaching_script_user_prompt(topic, subject, state.lecture_plan),
                usage=ctx.usage,
            )
            state.teaching_script = teaching_script_to_payload(script_result.output)
        except Exception as exc:
            print(
                f"teaching script error: {format_custom_endpoint_error(str(exc))}",
                file=sys.stderr,
                flush=True,
            )
    coder_result = await run_coder_step(
        topic,
        subject,
        state.lecture_plan,
        teaching_script=state.teaching_script,
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

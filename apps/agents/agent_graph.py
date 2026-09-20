"""Animus Agent Graph — Declarative Pydantic Graph Pipeline for Educational Animations.

Architecture:
    ClassifyNode -> PlanLectureNode -> PlanTeachingScriptNode -> CodeAgentNode
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any
import uuid

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_graph import BaseNode, End, EndMarker, GraphBuilder, GraphRunContext

from classifier_agent import classifier_agent
from cinematic_director import is_cinematic_mode
from coder_run import CoderRunResult
from coder_step import run_coder_step, subject_str
from ir.manim_ir import Classification, Lecture, Subject
from lecture_planner import lecture_planner_agent
from llm_config import model_for_agent, settings_for
from llm_retry import execute_with_llm_retry
from observability import configure_logfire
from openai_compatible import format_custom_endpoint_error
from teaching_script import (
    TeachingScript,
    teaching_script_agent,
    teaching_script_user_prompt,
)

load_dotenv()
configure_logfire()


# ==============================================================================
# Pipeline State Definition
# ==============================================================================


@dataclass
class AnimationState:
    """Shared state passed through the Pydantic Graph execution lifecycle."""

    user_query: str
    target_length: str = "medium"
    cinematic: bool = False
    classification: Classification | None = None
    plan: Lecture | None = None
    teaching_script: TeachingScript | None = None
    code: str | None = None
    run_dir: str | None = None
    coder_result: CoderRunResult | None = None
    prompt_index: int | None = None
    animation_mode: str = "keyframe"


# ==============================================================================
# Graph Node Definitions
# ==============================================================================


@dataclass
class ClassifyNode(BaseNode[AnimationState, None, str]):
    """Classifies user request into domain subject and verified topic."""

    async def run(
        self, ctx: GraphRunContext[AnimationState]
    ) -> PlanLectureNode | End[str]:
        classify_error: str | None = None
        try:
            async def _call_classify():
                return await classifier_agent.run(ctx.state.user_query)

            result = await execute_with_llm_retry(
                _call_classify, operation_name="Classifier Agent"
            )
            ctx.state.classification = result.output
        except Exception as exc:
            classify_error = format_custom_endpoint_error(exc)
            print(f"classifier error: {classify_error}", file=sys.stderr, flush=True)
            ctx.state.classification = None

        if (
            ctx.state.classification is None
            or ctx.state.classification.subject == Subject.UNKNOWN
        ):
            detail = "Domain not supported or classification failed."
            if classify_error:
                detail = f"{detail} ({classify_error[:400]})"
            return End(detail)

        return PlanLectureNode()


@dataclass
class PlanLectureNode(BaseNode[AnimationState, None, str]):
    """Produces the high-level pedagogical outline using manim-composer and manimce-best-practices."""

    async def run(
        self, ctx: GraphRunContext[AnimationState]
    ) -> PlanTeachingScriptNode | End[str]:
        plan_error: str | None = None
        classification = ctx.state.classification
        topic = classification.topic if classification else "Math Topic"
        subject = classification.subject if classification else Subject.MATH

        try:
            async def _call_planner():
                planner_prompt = (
                    f"Topic: {topic}\n"
                    f"Subject: {subject_str(subject)}\n"
                    f"Target Length: {ctx.state.target_length}\n"
                    f"Cinematic: {ctx.state.cinematic}\n\n"
                    "Consult `manim-composer` to craft a clear pedagogical narrative arc, hook, pacing, and aha moment. "
                    "Consult `manimce-best-practices` to ensure equations, diagrams, and layouts adhere to Manim CE frame-safe standards."
                )
                return await lecture_planner_agent.run(planner_prompt)

            result = await execute_with_llm_retry(
                _call_planner, operation_name="Lecture Planner Agent"
            )
            ctx.state.plan = result.output
        except Exception as exc:
            plan_error = format_custom_endpoint_error(exc)
            print(f"planner error: {plan_error}", file=sys.stderr, flush=True)
            ctx.state.plan = None

        if ctx.state.plan is None:
            detail = "Lecture planning failed."
            if plan_error:
                detail = f"{detail} ({plan_error[:400]})"
            return End(detail)

        return PlanTeachingScriptNode()


@dataclass
class PlanTeachingScriptNode(BaseNode[AnimationState, None, str]):
    """Generates sequential narration beats aligned with visual actions."""

    async def run(
        self, ctx: GraphRunContext[AnimationState]
    ) -> CodeAgentNode:
        classification = ctx.state.classification
        plan = ctx.state.plan
        if classification is None or plan is None:
            return CodeAgentNode()

        try:
            async def _call_teaching_script():
                return await teaching_script_agent.run(
                    teaching_script_user_prompt(
                        classification.topic,
                        subject_str(classification.subject),
                        plan,
                        length=ctx.state.target_length,
                        cinematic=ctx.state.cinematic,
                    )
                )

            result = await execute_with_llm_retry(
                _call_teaching_script, operation_name="Teaching Script Agent"
            )
            ctx.state.teaching_script = result.output
        except Exception as exc:
            print(
                f"teaching script error: {format_custom_endpoint_error(str(exc))}",
                file=sys.stderr,
                flush=True,
            )
            ctx.state.teaching_script = None

        return CodeAgentNode()


@dataclass
class CodeAgentNode(BaseNode[AnimationState, None, str]):
    """Synthesizes, compiles, and verifies the final Manim scene code."""

    async def run(self, ctx: GraphRunContext[AnimationState]) -> End[str]:
        assert ctx.state.classification is not None, "Classification required for code agent"
        coder_result = await run_coder_step(
            ctx.state.classification.topic,
            ctx.state.classification.subject,
            ctx.state.plan,
            teaching_script=ctx.state.teaching_script,
            user_prompt=ctx.state.user_query,
            prompt_index=ctx.state.prompt_index,
            length=ctx.state.target_length,
            cinematic=ctx.state.cinematic,
            animation_mode=ctx.state.animation_mode,
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


# Backward compatibility alias
CodeAgent = CodeAgentNode


# ==============================================================================
# Graph Builder & Assembly
# ==============================================================================

_builder = GraphBuilder(
    state_type=AnimationState, output_type=str, name="Manim Animation Graph"
)


@_builder.step
async def _start(state: AnimationState) -> ClassifyNode:
    return ClassifyNode()


_builder.add(
    _builder.node(ClassifyNode),
    _builder.node(PlanLectureNode),
    _builder.node(PlanTeachingScriptNode),
    _builder.node(CodeAgentNode),
    _builder.edge_from(_builder.start_node).to(_start),
)

animation_graph = _builder.build()


# ==============================================================================
# Storage & Execution Helpers
# ==============================================================================


def _find_compiled_video(run_dir: str | None) -> Path | None:
    """Locate the compiled MP4 in the run directory, inspecting manifest.json first."""
    if not run_dir:
        return None
    root = Path(run_dir)
    if not root.is_dir():
        return None

    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        try:
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


def _upload_pipeline_artifacts(
    result: dict[str, Any], coder_result: CoderRunResult
) -> None:
    """Upload video and Python scene files to MinIO/S3 if configured."""
    if not os.getenv("S3_VIDEO_ENDPOINT"):
        return

    try:
        from tools.minio_storage import upload_to_minio

        video_path = _find_compiled_video(coder_result.run_dir)
        if video_path and video_path.is_file():
            gen_id = uuid.uuid4()
            video_key = f"videos/pipeline/{gen_id}.mp4"
            code_key = f"videos/pipeline/{gen_id}.py"

            video_url = upload_to_minio(
                video_path, object_key=video_key, content_type="video/mp4"
            )
            result["minio_url"] = video_url
            result["minio_key"] = video_key
            print(f"[minio] Uploaded video to {video_url}", file=sys.stderr, flush=True)

            if coder_result.scene_file:
                scene_path = Path(coder_result.run_dir) / coder_result.scene_file
                if scene_path.is_file():
                    code_url = upload_to_minio(
                        scene_path, object_key=code_key, content_type="text/x-python"
                    )
                    result["code_minio_url"] = code_url
                    result["code_minio_key"] = code_key
                    print(
                        f"[minio] Uploaded scene code to {code_url}",
                        file=sys.stderr,
                        flush=True,
                    )
    except Exception as exc:
        print(f"[minio] Upload failed: {exc}", file=sys.stderr, flush=True)


# ==============================================================================
# Pipeline Entry Point
# ==============================================================================


async def run_pipeline(
    user_query: str,
    *,
    length: str = "medium",
    cinematic: bool = False,
    prompt_index: int | None = None,
    mode: str = "keyframe",
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Execute the animation pipeline, routing between keyframe engine and graph."""
    if mode == "keyframe":
        from keyframe_engine import run_producer_consumer

        total_slides = 3
        if length in ("5m", "medium", "5"):
            total_slides = 3
        elif length in ("10m", "long", "10"):
            total_slides = 4
        elif length in ("short", "1m", "1"):
            total_slides = 2

        res = await asyncio.to_thread(
            run_producer_consumer,
            user_query,
            output_dir=output_dir,
            total_slides=total_slides,
        )
        if res.get("scene_file") and not res.get("scene_path"):
            res["scene_path"] = res["scene_file"]
        return res

    cinematic_active = is_cinematic_mode(user_query, flag=cinematic)
    state = AnimationState(
        user_query=user_query,
        target_length=length,
        cinematic=cinematic_active,
        prompt_index=prompt_index,
        animation_mode=mode,
    )

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
        raise RuntimeError(format_custom_endpoint_error(exc)) from exc

    if state.coder_result is not None:
        result = state.coder_result.model_dump(mode="json")
        if prompt_index is not None:
            result["prompt_index"] = prompt_index
        _upload_pipeline_artifacts(result, state.coder_result)
        return result

    return {
        "result": summary,
        "stopped_reason": "classification_failed_or_unsupported",
        "error": summary or "classification_failed_or_unsupported",
        "message": summary or "Domain not supported or classification failed.",
    }


# ==============================================================================
# Interactive Pydantic AI Agent Interface
# ==============================================================================


class PipelineResult(BaseModel):
    result: str
    stopped_reason: str
    compile_ok: bool
    scene_name: str | None = None
    run_dir: str | None = None
    audio: int | None = None
    error: str | None = None
    message: str | None = None


animation_agent = Agent(
    model_for_agent("animation"),
    name="Manim Animation Pipeline",
    description="Runs the full educational animation graph pipeline.",
    model_settings=settings_for("animation"),
    system_prompt=(
        "You are the interactive frontend for the Manim animation pipeline.\n"
        "Call `generate_educational_animation` with the user's exact query to start the generation.\n"
        "Do not write long reasoning or preambles, just call the tool."
    ),
)


@animation_agent.tool
async def generate_educational_animation(
    ctx: RunContext, user_query: str
) -> PipelineResult:
    """Execute the full animation pipeline (classify, plan, script, code, compile) for the user's query."""
    result = await run_pipeline(user_query)

    return PipelineResult(
        result=result.get("result", result.get("summary", "")),
        stopped_reason=result.get("stopped_reason", "unknown"),
        compile_ok=result.get("compile_ok", False),
        scene_name=result.get("scene_name"),
        run_dir=result.get("run_dir"),
        audio=len(result.get("audio_paths", [])),
        error=result.get("error"),
        message=result.get("message"),
    )


if __name__ == "__main__":
    prompt = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "I want to learn about Hairy Ball theorem."
    )
    result = asyncio.run(run_pipeline(prompt))
    print(result)

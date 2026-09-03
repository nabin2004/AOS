"""Robust agent workflow loop for Manim animation + voiceover generation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic_ai import Agent, AgentRunResult

from educlaw.agent.deps import AgentDeps
from educlaw.animateworkflow import contracts
from educlaw.animateworkflow.compiler import compile_final_code
from educlaw.animateworkflow.contracts import (
    CompileError,
    CompileResult,
    FailureCategory,
    FinalCode,
    LessonPlan,
    NarrationPlan,
    PipelineState,
    RequestClassification,
)
from educlaw.animateworkflow.prompts import (
    CODE_GENERATOR_INSTRUCTIONS,
    NARRATION_PLANNER_INSTRUCTIONS,
)
from educlaw.animateworkflow.components import get_components_prompt_injection
from educlaw.animateworkflow.theme import EduClawTheme, get_theme
from educlaw.animateworkflow.visual_qc import inspect_video_frames
from educlaw.memory.files import append_memory_digest
from educlaw.memory.store import IngestUnavailable
from educlaw.settings import Settings

logger = logging.getLogger(__name__)

MAX_COMPILATION_REPLANS = 3

CATEGORY_GUIDANCE = {
    FailureCategory.HALLUCINATED_KWARGS: (
        "Do NOT call Background(...) or pass Voiceover(...) directly into self.play(...). "
        "Use 'with self.voiceover(text=...) as tracker:' context manager instead."
    ),
    FailureCategory.MISSING_IMPORTS: (
        "Ensure all necessary classes are imported: 'from manim_voiceover import VoiceoverScene', "
        "'from manim import *', etc."
    ),
    FailureCategory.MALFORMED_POINT_ARRAYS: (
        "Ensure ParametricFunction takes 'function=lambda t: np.array([x, y, z])', "
        "not a 'points' parameter. Verify all coordinate tuples/arrays are 3D (x, y, z)."
    ),
    FailureCategory.LATEX_ERROR: (
        "Check MathTex / Tex formatting. Use raw Python strings r'...' and verify valid LaTeX syntax."
    ),
    FailureCategory.SYNTAX_ERROR: (
        "Ensure valid Python 3 syntax with correct indentation and matching brackets/parentheses."
    ),
    FailureCategory.RENDER_TIMEOUT: (
        "Render exceeded timeout limit. Reduce scene run_time durations, simplify complex loops, "
        "or lower point sampling resolution."
    ),
    FailureCategory.VISUAL_DEFECT: (
        "Re-adjust element coordinates and layout to prevent overlapping or clipping off-screen. "
        "Use .arrange(DOWN, buff=...) and keep formulas within bounding frame limits."
    ),
}


def build_agents(
    settings: Settings | None = None,
    *,
    model: str | object | None = None,
) -> tuple[
    Agent[object, RequestClassification],
    Agent[object, contracts.LessonPlan],
    Agent[object, NarrationPlan],
    Agent[object, FinalCode],
]:
    """Build the agents used in the animation & voiceover pipeline."""
    if model is not None:
        resolved_model = model
    elif settings and settings.test_model:
        from pydantic_ai.models.test import TestModel

        resolved_model = TestModel(call_tools=[], custom_output_text="ok")
    elif settings and settings.model:
        resolved_model = settings.model
    else:
        resolved_model = "openrouter:openai/gpt-4o-mini"

    return (
        Agent(
            model=resolved_model,
            name="RequestAnalyser",
            output_type=RequestClassification,
            instructions="You are a helpful assistant that classifies user requests for educational video content.",
        ),
        Agent(
            model=resolved_model,
            name="ScenePlannerAgent",
            output_type=contracts.LessonPlan,
            instructions="You are a helpful assistant that plans the scenes needed to fulfill user requests for educational video content.",
        ),
        Agent(
            model=resolved_model,
            name="NarrationPlannerAgent",
            output_type=NarrationPlan,
            instructions=NARRATION_PLANNER_INSTRUCTIONS,
        ),
        Agent(
            model=resolved_model,
            name="CodeGeneratorAgent",
            instructions=CODE_GENERATOR_INSTRUCTIONS,
            output_type=FinalCode,
        ),
    )


def normalize_lesson_plan(
    plan: LessonPlan, classification: RequestClassification
) -> LessonPlan:
    """Ensure all video IDs in the lesson plan match the request classification ID."""
    normalized = plan.model_copy(
        update={
            "videos": [
                video.model_copy(update={"video_id": classification.video_id})
                for video in plan.videos
            ]
        }
    )
    return normalized.validate_video_ids(classification.video_id)


class WorkflowOrchestrator:
    """Robust agent orchestrator for educational Manim animation + voiceover generation."""

    def __init__(
        self,
        agents: tuple[
            Agent[object, RequestClassification],
            Agent[object, contracts.LessonPlan],
            Agent[object, NarrationPlan],
            Agent[object, FinalCode],
        ]
        | None = None,
        *,
        deps: AgentDeps | None = None,
        settings: Settings | None = None,
        theme: str | EduClawTheme | None = None,
        inspect_visual: bool = False,
        max_replans: int = MAX_COMPILATION_REPLANS,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.deps = deps
        self.agents = agents or build_agents(self.settings)
        self.theme = theme if isinstance(theme, EduClawTheme) else get_theme(theme)
        self.inspect_visual = inspect_visual
        self.max_replans = max_replans
        self.state = PipelineState()
        self.history: list[dict[str, Any]] = []

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        if self.deps and self.deps.emit:
            self.deps.emit(event, payload)

    async def _retrieve_memory_context(self, user_request: str) -> str:
        if not self.deps or not self.deps.memory:
            return ""
        try:
            retrieved = await self.deps.memory.retrieve(user_request, top_k=5)
            if retrieved:
                return f"\n\n## Context from past memory graph:\n{retrieved}\n"
        except Exception as exc:
            logger.debug("Memory retrieval skipped: %s", exc)
        return ""

    async def step_classify(self, user_request: str) -> RequestClassification:
        """Step 1: Classify educational intent and video configuration."""
        self._emit("workflow_step_start", {"step": 1, "name": "request_analysis"})
        memory_ctx = await self._retrieve_memory_context(user_request)
        prompt = f"{user_request}{memory_ctx}"

        analyser = self.agents[0]
        result: AgentRunResult[RequestClassification] = await analyser.run(prompt)
        classification = result.output
        self.state.request = classification
        self.history.append({"step": "classification", "output": classification.model_dump()})
        self._emit(
            "workflow_step_complete",
            {"step": 1, "name": "request_analysis", "output": classification.model_dump()},
        )
        return classification

    async def step_scene_plan(
        self, user_request: str, classification: RequestClassification
    ) -> LessonPlan:
        """Step 2: Plan structured visual scenes and animation steps."""
        self._emit("workflow_step_start", {"step": 2, "name": "scene_planning"})
        scene_planner = self.agents[1]
        scene_prompt = (
            f"Request:\n{user_request}\n\n"
            f"Classification:\n{classification.model_dump_json()}"
        )
        scene_result: AgentRunResult[contracts.LessonPlan] = await scene_planner.run(scene_prompt)
        lesson_plan = normalize_lesson_plan(scene_result.output, classification)
        self.state.lesson_plan = lesson_plan
        self.history.append({"step": "scene_plan", "output": lesson_plan.model_dump()})
        self._emit(
            "workflow_step_complete",
            {"step": 2, "name": "scene_planning", "output": lesson_plan.model_dump()},
        )
        return lesson_plan

    async def step_narration_plan(
        self,
        user_request: str,
        classification: RequestClassification,
        lesson_plan: LessonPlan,
    ) -> NarrationPlan:
        """Step 3: Plan voiceover narration and bookmark synchronization."""
        self._emit("workflow_step_start", {"step": 3, "name": "narration_planning"})
        narration_planner = self.agents[2]
        scene_plan_json = lesson_plan.model_dump_json()
        narration_prompt = (
            f"Request:\n{user_request}\n\n"
            f"Classification:\n{classification.model_dump_json()}\n\n"
            f"Lesson plan:\n{scene_plan_json}"
        )
        narration_result: AgentRunResult[NarrationPlan] = await narration_planner.run(narration_prompt)
        narration_plan = narration_result.output
        # Immediate validation gate: verify scene IDs
        narration_plan.validate_scene_ids(lesson_plan)
        self.state.narration_plan = narration_plan
        self.history.append({"step": "narration_plan", "output": narration_plan.model_dump()})
        self._emit(
            "workflow_step_complete",
            {"step": 3, "name": "narration_planning", "output": narration_plan.model_dump()},
        )
        return narration_plan

    def _format_error_guidance(self, errors: list[CompileError]) -> str:
        """Build targeted diagnostic instructions for the Code Generator."""
        parts = []
        for err in errors:
            guidance = CATEGORY_GUIDANCE.get(err.category, "")
            line_info = f" (line {err.line})" if err.line else ""
            part = f"- [{err.category.value}]{line_info}: {err.message}"
            if guidance:
                part += f"\n  -> Recommendation: {guidance}"
            parts.append(part)
        return "\n".join(parts)

    async def step_generate_and_compile(
        self,
        user_request: str,
        lesson_plan: LessonPlan,
        narration_plan: NarrationPlan,
        workspace_dir: Path | None = None,
    ) -> tuple[FinalCode | None, CompileResult]:
        """Step 4 & 5: Code generation with sandbox preflight & compile replanning loop."""
        cwd = workspace_dir or (self.deps.cwd if self.deps else Path.cwd())
        code_generator = self.agents[3]

        scene_plan_json = lesson_plan.model_dump_json()
        narration_json = narration_plan.model_dump_json()

        compile_error_details: str | None = None
        final_code: FinalCode | None = None
        last_compile_result: CompileResult | None = None

        for attempt in range(1, self.max_replans + 1):
            self._emit(
                "workflow_step_start",
                {"step": 4, "name": "code_generation", "attempt": attempt, "max": self.max_replans},
            )

            theme_ctx = (
                f"## Active Theme & Styling Constants:\n"
                f"```python\n{self.theme.to_manim_constants()}```\n\n"
                f"{get_components_prompt_injection()}"
            )
            prompt_parts = [
                f"User request:\n{user_request}",
                theme_ctx,
                f"Scene plan:\n{scene_plan_json}",
                f"Narration plan:\n{narration_json}",
            ]
            if compile_error_details:
                prompt_parts.append(
                    f"Previous attempt #{attempt - 1} failed compilation with errors:\n"
                    f"{compile_error_details}\n\n"
                    f"Please fix all issues and generate the complete, working Python script."
                )

            code_result: AgentRunResult[FinalCode] = await code_generator.run("\n\n".join(prompt_parts))
            final_code = code_result.output
            self.state.final_code = final_code

            self._emit(
                "workflow_step_complete",
                {
                    "step": 4,
                    "name": "code_generation",
                    "attempt": attempt,
                    "scene_name": final_code.scene_name,
                },
            )

            # Step 5: Compile & Verify
            self._emit(
                "workflow_step_start",
                {"step": 5, "name": "compilation_verification", "attempt": attempt},
            )
            compile_result = compile_final_code(
                final_code,
                cwd=cwd,
                quality=self.settings.manim_quality if self.settings else "l",
            )
            self.state.compile_result = compile_result
            last_compile_result = compile_result

            if compile_result.success:
                # Multimodal Visual QA check if enabled
                if self.inspect_visual and compile_result.output_path:
                    qc_frames_dir = cwd / ".educlaw" / "qc_frames"
                    is_mock = getattr(self.settings, "test_model", False) or False
                    qc_report = await inspect_video_frames(
                        Path(compile_result.output_path),
                        qc_frames_dir,
                        mock=is_mock,
                    )
                    self.state.visual_qc_report = qc_report
                    if not qc_report.passed and attempt < self.max_replans:
                        defect_descriptions = [
                            f"At {f.timestamp_sec}s: {f.description}. Fix: {f.suggested_fix}"
                            for f in qc_report.inspected_frames
                            if f.has_overlaps or f.has_clipping or f.contrast_issue
                        ]
                        compile_error_details = (
                            f"[VISUAL_DEFECT]: Visual inspection detected rendering defects:\n"
                            + "\n".join(defect_descriptions)
                        )
                        self._emit(
                            "workflow_step_complete",
                            {
                                "step": 5,
                                "name": "compilation_verification",
                                "attempt": attempt,
                                "success": False,
                                "visual_defects": defect_descriptions,
                            },
                        )
                        continue

                self._emit(
                    "workflow_step_complete",
                    {
                        "step": 5,
                        "name": "compilation_verification",
                        "attempt": attempt,
                        "success": True,
                        "output_path": compile_result.output_path,
                    },
                )
                break

            compile_error_details = self._format_error_guidance(compile_result.errors)
            self._emit(
                "workflow_step_complete",
                {
                    "step": 5,
                    "name": "compilation_verification",
                    "attempt": attempt,
                    "success": False,
                    "errors": [err.model_dump() for err in compile_result.errors],
                },
            )
        else:
            if last_compile_result is None:
                last_compile_result = CompileResult(
                    success=False,
                    errors=[
                        CompileError(
                            category=FailureCategory.RENDER_ERROR,
                            message=f"Failed to generate code after {self.max_replans} attempts",
                        )
                    ],
                )

        return final_code, last_compile_result

    async def ingest_memory(self, user_request: str, state: PipelineState) -> None:
        """Store workflow results into Dagestan temporal memory graph."""
        if not self.deps or not self.deps.memory:
            return

        conversation = [
            {"role": "user", "content": user_request},
            {
                "role": "assistant",
                "content": (
                    f"Generated Manim animation for topic '{state.request.topic if state.request else 'topic'}'. "
                    f"Video compile success: {state.compile_result.success if state.compile_result else False}. "
                    f"Scene name: {state.final_code.scene_name if state.final_code else 'N/A'}."
                ),
            },
        ]
        try:
            await self.deps.memory.ingest(conversation, source="animateworkflow")
        except IngestUnavailable:
            self._emit("memory_skip", {"reason": "ingest_unavailable"})
        except Exception as exc:
            logger.debug("Memory ingestion error: %s", exc)

        if state.compile_result and state.compile_result.success and self.deps.cwd:
            topic = state.request.topic if state.request else "video"
            digest = f"AnimateWorkflow: Rendered '{topic}' scene '{state.final_code.scene_name if state.final_code else ''}' successfully."
            append_memory_digest(self.deps.cwd, digest)

    async def run(
        self,
        user_request: str,
        *,
        workspace_dir: Path | None = None,
    ) -> PipelineState:
        """Execute the complete robust multi-agent Manim & voiceover generation pipeline."""
        classification = await self.step_classify(user_request)
        lesson_plan = await self.step_scene_plan(user_request, classification)
        narration_plan = await self.step_narration_plan(user_request, classification, lesson_plan)
        final_code, compile_result = await self.step_generate_and_compile(
            user_request,
            lesson_plan,
            narration_plan,
            workspace_dir=workspace_dir,
        )

        await self.ingest_memory(user_request, self.state)
        self.log_trajectory(user_request, workspace_dir=workspace_dir)
        return self.state

    def log_trajectory(self, user_request: str, workspace_dir: Path | None = None) -> Path | None:
        """Persist execution trajectory and prompt interaction to .aos/trajectories/ in JSONL format."""
        import json
        import time

        cwd = workspace_dir or (self.deps.cwd if self.deps else Path.cwd())
        traj_dir = cwd / ".aos" / "trajectories"
        traj_dir.mkdir(parents=True, exist_ok=True)

        video_id = str(self.state.request.video_id) if self.state.request else "unknown"
        filename = f"traj_{int(time.time())}_{video_id[:8]}.jsonl"
        traj_path = traj_dir / filename

        entry = {
            "timestamp": time.time(),
            "request": user_request,
            "topic": self.state.request.topic if self.state.request else "",
            "theme": self.theme.name,
            "success": self.state.compile_result.success if self.state.compile_result else False,
            "scene_name": self.state.final_code.scene_name if self.state.final_code else "",
            "history": self.history,
            "final_code": self.state.final_code.code if self.state.final_code else "",
            "compile_errors": [
                err.model_dump() for err in self.state.compile_result.errors
            ] if self.state.compile_result and self.state.compile_result.errors else [],
        }

        try:
            with open(traj_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
            return traj_path
        except Exception as exc:
            logger.debug("Failed to write trajectory log: %s", exc)
            return None


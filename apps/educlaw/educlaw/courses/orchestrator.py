"""Course and Lecture Series Orchestrator for EduClaw."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic_ai import Agent, AgentRunResult

from educlaw.agent.deps import AgentDeps
from educlaw.animateworkflow.compiler import compile_final_code
from educlaw.animateworkflow.contracts import (
    Audience,
    CompileError,
    CompileResult,
    FailureCategory,
    FinalCode,
    LessonPlan,
    NarrationPlan,
)
from educlaw.animateworkflow.loop import (
    CATEGORY_GUIDANCE,
    MAX_COMPILATION_REPLANS,
    normalize_lesson_plan,
)
from educlaw.courses.agents import (
    build_curriculum_agent,
    build_lecture_code_agent,
    build_lecture_narration_agent,
    build_lecture_notes_agent,
    build_lecture_scene_agent,
)
from educlaw.courses.contracts import (
    Course,
    CourseSyllabus,
    Lecture,
    LectureSpec,
    RenderStatus,
)
from educlaw.courses.storage import (
    get_course_dir,
    load_course,
    save_course,
)
from educlaw.memory.files import append_memory_digest
from educlaw.memory.store import IngestUnavailable
from educlaw.settings import Settings

logger = logging.getLogger(__name__)


class CourseOrchestrator:
    """Orchestrates multi-agent curriculum planning, lecture animation, narration,

    sandbox rendering, and companion notes generation for educational courses.
    """

    def __init__(
        self,
        agents: tuple[
            Agent[object, CourseSyllabus],
            Agent[object, LessonPlan],
            Agent[object, NarrationPlan],
            Agent[object, FinalCode],
            Agent[object, str],
        ]
        | None = None,
        *,
        deps: AgentDeps | None = None,
        settings: Settings | None = None,
        max_replans: int = MAX_COMPILATION_REPLANS,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.deps = deps
        self.max_replans = max_replans

        if agents is not None:
            self.curriculum_agent, self.scene_agent, self.narration_agent, self.code_agent, self.notes_agent = agents
        else:
            self.curriculum_agent = build_curriculum_agent(self.settings)
            self.scene_agent = build_lecture_scene_agent(self.settings)
            self.narration_agent = build_lecture_narration_agent(self.settings)
            self.code_agent = build_lecture_code_agent(self.settings)
            self.notes_agent = build_lecture_notes_agent(self.settings)

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        if self.deps and self.deps.emit:
            self.deps.emit(event, payload)

    async def _retrieve_memory_context(self, query: str) -> str:
        if not self.deps or not self.deps.memory:
            return ""
        try:
            retrieved = await self.deps.memory.retrieve(query, top_k=5)
            if retrieved:
                return f"\n\n## Context from past course memory graph:\n{retrieved}\n"
        except Exception as exc:
            logger.debug("Memory retrieval skipped: %s", exc)
        return ""

    def _format_error_guidance(self, errors: list[CompileError]) -> str:
        parts = []
        for err in errors:
            guidance = CATEGORY_GUIDANCE.get(err.category, "")
            line_info = f" (line {err.line})" if err.line else ""
            part = f"- [{err.category.value}]{line_info}: {err.message}"
            if guidance:
                part += f"\n  -> Recommendation: {guidance}"
            parts.append(part)
        return "\n".join(parts)

    async def plan_syllabus(
        self,
        topic: str,
        *,
        num_lectures: int = 3,
        audience: Audience = Audience.EXPLORING,
        subject: str = "General",
        workspace_dir: Path | None = None,
    ) -> Course:
        """Step 1: Plan complete curriculum, syllabus, and global visual grammar."""
        self._emit(
            "course_syllabus_start",
            {"topic": topic, "num_lectures": num_lectures, "audience": audience.value},
        )

        memory_ctx = await self._retrieve_memory_context(topic)
        prompt = (
            f"Course Topic: {topic}\n"
            f"Subject: {subject}\n"
            f"Target Audience: {audience.value}\n"
            f"Total Lectures Requested: {num_lectures}\n\n"
            f"Design a complete, mathematically and conceptually rigorous course syllabus "
            f"with exactly {num_lectures} lectures. Establish a cohesive visual grammar.\n"
            f"{memory_ctx}"
        )

        result: AgentRunResult[CourseSyllabus] = await self.curriculum_agent.run(prompt)
        syllabus = result.output

        cwd = workspace_dir or (self.deps.cwd if self.deps else Path.cwd())
        course = Course.from_syllabus(syllabus, workspace_dir=cwd)
        save_course(course, workspace_dir=cwd)

        self._emit(
            "course_syllabus_complete",
            {
                "course_id": str(course.course_id),
                "title": course.title,
                "slug": course.slug,
                "total_lectures": len(course.lectures),
            },
        )
        return course

    def _build_lecture_context(self, course: Course, lecture_number: int) -> str:
        """Construct cumulative context from earlier lectures in the series."""
        earlier_lectures = [lec for lec in course.lectures if lec.lecture_number < lecture_number]
        if not earlier_lectures:
            return "This is Lecture 1 (Foundational Introduction). Establish core definitions and visual motifs."

        context_lines = [
            "### Course Progression & Context from Earlier Lectures in this Series:",
            f"Course Title: {course.title}",
            f"Global Visual Grammar: Palette={course.syllabus.visual_grammar.theme_name} "
            f"(Primary={course.syllabus.visual_grammar.primary_color}, "
            f"Secondary={course.syllabus.visual_grammar.secondary_color})",
            "",
        ]
        for lec in earlier_lectures:
            context_lines.append(f"Lecture {lec.lecture_number}: {lec.spec.title}")
            context_lines.append(f"  - Concepts Covered: {', '.join(lec.spec.key_concepts)}")
            if lec.spec.prerequisites_from_course:
                context_lines.append(f"  - Established Prerequisites: {', '.join(lec.spec.prerequisites_from_course)}")
            context_lines.append("")

        return "\n".join(context_lines)

    async def generate_lecture(
        self,
        course: Course,
        lecture_number: int,
        *,
        render: bool = True,
        quality: str = "m",
        workspace_dir: Path | None = None,
    ) -> Lecture:
        """Generate and optionally compile an individual lecture in the course."""
        lecture = course.get_lecture(lecture_number)
        if lecture is None:
            raise ValueError(f"Lecture {lecture_number} not found in course '{course.slug}'")

        cwd = workspace_dir or (self.deps.cwd if self.deps else Path.cwd())
        self._emit(
            "course_lecture_start",
            {
                "course_slug": course.slug,
                "lecture_number": lecture_number,
                "title": lecture.spec.title,
            },
        )

        prior_context = self._build_lecture_context(course, lecture_number)

        # 1. Scene Planning
        scene_prompt = (
            f"Course: {course.title}\n"
            f"Subject: {course.syllabus.subject}\n"
            f"Visual Grammar: {course.syllabus.visual_grammar.model_dump_json()}\n\n"
            f"{prior_context}\n\n"
            f"Current Lecture #{lecture.lecture_number}: {lecture.spec.title}\n"
            f"Lecture Description: {lecture.spec.description}\n"
            f"Key Concepts: {', '.join(lecture.spec.key_concepts)}\n"
            f"Visual Goals: {', '.join(lecture.spec.visual_goals)}\n"
        )
        scene_result: AgentRunResult[LessonPlan] = await self.scene_agent.run(scene_prompt)
        lesson_plan = scene_result.output
        lecture.scene_plan = lesson_plan
        lecture.status = RenderStatus.PLANNED

        # 2. Narration Planning
        narration_prompt = (
            f"Course: {course.title}\n"
            f"{prior_context}\n\n"
            f"Lecture #{lecture.lecture_number}: {lecture.spec.title}\n"
            f"Visual Scene Plan:\n{lesson_plan.model_dump_json()}\n"
        )
        narration_result: AgentRunResult[NarrationPlan] = await self.narration_agent.run(narration_prompt)
        narration_plan = narration_result.output
        
        # Align scene IDs to lesson plan scenes if needed
        valid_scene_ids = [scene.scene_id for video in lesson_plan.videos for scene in video.scenes]
        if valid_scene_ids and narration_plan.steps:
            for idx, step in enumerate(narration_plan.steps):
                if step.scene_id not in valid_scene_ids:
                    step.scene_id = valid_scene_ids[min(idx, len(valid_scene_ids) - 1)]

        try:
            narration_plan.validate_scene_ids(lesson_plan)
        except ValueError as exc:
            logger.warning("Narration scene ID validation warning: %s", exc)
        lecture.narration_plan = narration_plan

        # 3. Code Generation & Sandbox Compile Loop
        compile_error_details: str | None = None
        final_code: FinalCode | None = None
        last_compile_result: CompileResult | None = None

        for attempt in range(1, self.max_replans + 1):
            self._emit(
                "course_lecture_codegen_start",
                {"lecture_number": lecture_number, "attempt": attempt},
            )
            code_prompt_parts = [
                f"Course: {course.title}",
                f"Lecture #{lecture.lecture_number}: {lecture.spec.title}",
                f"Visual Grammar:\n{course.syllabus.visual_grammar.model_dump_json()}",
                f"Scene Plan:\n{lesson_plan.model_dump_json()}",
                f"Narration Plan:\n{narration_plan.model_dump_json()}",
            ]
            if compile_error_details:
                code_prompt_parts.append(
                    f"Previous attempt #{attempt - 1} failed compilation with errors:\n"
                    f"{compile_error_details}\n\n"
                    f"Please fix all issues and generate the complete, working Python Manim script."
                )

            code_result: AgentRunResult[FinalCode] = await self.code_agent.run("\n\n".join(code_prompt_parts))
            final_code = code_result.output
            lecture.final_code = final_code
            lecture.status = RenderStatus.CODED

            if not render:
                break

            # Render in sandbox
            compile_result = compile_final_code(
                final_code,
                cwd=cwd,
                quality=quality,
            )
            lecture.compile_result = compile_result
            last_compile_result = compile_result

            if compile_result.success:
                lecture.status = RenderStatus.RENDERED
                # Copy render output to course lecture folder
                if compile_result.output_path and Path(compile_result.output_path).exists():
                    target_render_dir = get_course_dir(course.slug, cwd) / f"lecture_{lecture.lecture_number:02d}" / "render"
                    target_render_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = target_render_dir / f"lecture_{lecture.lecture_number:02d}.mp4"
                    try:
                        shutil.copy2(compile_result.output_path, dest_file)
                        lecture.video_path = str(dest_file)
                    except Exception:
                        lecture.video_path = compile_result.output_path
                else:
                    lecture.video_path = compile_result.output_path
                break

            compile_error_details = self._format_error_guidance(compile_result.errors)

        if render and (last_compile_result is None or not last_compile_result.success):
            lecture.status = RenderStatus.FAILED
            lecture.error_message = (
                compile_error_details or "Failed to compile lecture animation."
            )

        # 4. Companion Study Notes Generation
        notes_prompt = (
            f"Course: {course.title}\n"
            f"Lecture #{lecture.lecture_number}: {lecture.spec.title}\n"
            f"Description: {lecture.spec.description}\n"
            f"Key Concepts: {', '.join(lecture.spec.key_concepts)}\n"
            f"Generate comprehensive, beautiful Markdown study companion notes with LaTeX formulas and self-quiz."
        )
        notes_result: AgentRunResult[str] = await self.notes_agent.run(notes_prompt)
        lecture.study_notes = notes_result.output

        # 5. Persist Course state
        save_course(course, workspace_dir=cwd)

        # 6. Ingest into Dagestan Memory
        await self._ingest_lecture_memory(course, lecture)

        self._emit(
            "course_lecture_complete",
            {
                "course_slug": course.slug,
                "lecture_number": lecture_number,
                "status": lecture.status.value,
                "video_path": lecture.video_path,
            },
        )
        return lecture

    async def _ingest_lecture_memory(self, course: Course, lecture: Lecture) -> None:
        """Record lecture progress and concepts into Dagestan memory graph."""
        if not self.deps or not self.deps.memory:
            return

        conversation = [
            {"role": "user", "content": f"Generate course lecture {lecture.lecture_number}: {lecture.spec.title}"},
            {
                "role": "assistant",
                "content": (
                    f"Generated Course '{course.title}' Lecture {lecture.lecture_number} ('{lecture.spec.title}'). "
                    f"Concepts: {', '.join(lecture.spec.key_concepts)}. "
                    f"Status: {lecture.status.value}. "
                    f"Scene: {lecture.final_code.scene_name if lecture.final_code else 'N/A'}."
                ),
            },
        ]
        try:
            await self.deps.memory.ingest(conversation, source="courses_workflow")
        except IngestUnavailable:
            pass
        except Exception as exc:
            logger.debug("Course memory ingestion error: %s", exc)

        if lecture.is_rendered and self.deps.cwd:
            digest = f"CourseEngine: Rendered '{course.title}' Lecture {lecture.lecture_number} ({lecture.spec.title}) successfully."
            append_memory_digest(self.deps.cwd, digest)

    async def generate_course(
        self,
        prompt: str,
        *,
        num_lectures: int = 3,
        audience: Audience = Audience.EXPLORING,
        subject: str = "General",
        render: bool = True,
        quality: str = "m",
        workspace_dir: Path | None = None,
    ) -> Course:
        """Step-by-step end-to-end course generation with optimal sequential lecture pipeline."""
        cwd = workspace_dir or (self.deps.cwd if self.deps else Path.cwd())

        # Phase 1: Curriculum Architecture
        course = await self.plan_syllabus(
            prompt,
            num_lectures=num_lectures,
            audience=audience,
            subject=subject,
            workspace_dir=cwd,
        )

        # Phase 2: Sequential Lecture Pipeline
        for spec in course.syllabus.lectures:
            await self.generate_lecture(
                course,
                spec.lecture_number,
                render=render,
                quality=quality,
                workspace_dir=cwd,
            )

        # Phase 3: Finalize & Save
        save_course(course, workspace_dir=cwd)
        return course

    async def resume_course(
        self,
        slug_or_id: str,
        *,
        render: bool = True,
        quality: str = "m",
        workspace_dir: Path | None = None,
    ) -> Course:
        """Resume generating unrendered or failed lectures in an existing course."""
        cwd = workspace_dir or (self.deps.cwd if self.deps else Path.cwd())
        course = load_course(slug_or_id, workspace_dir=cwd)
        if course is None:
            raise FileNotFoundError(f"Course '{slug_or_id}' not found in workspace.")

        for lecture in course.lectures:
            if lecture.status != RenderStatus.RENDERED:
                await self.generate_lecture(
                    course,
                    lecture.lecture_number,
                    render=render,
                    quality=quality,
                    workspace_dir=cwd,
                )

        save_course(course, workspace_dir=cwd)
        return course

"""Data contracts and schemas for Course and Lecture series generation."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from educlaw.animateworkflow.contracts import (
    Audience,
    CompileError,
    CompileResult,
    FailureCategory,
    FinalCode,
    LessonPlan,
    NarrationPlan,
    OutputType,
    SceneStep,
    VideoPlan,
    VisualStyle,
)


class GenerationMode(str, Enum):
    SINGLE = "single"
    COURSE = "course"


class RenderStatus(str, Enum):
    PENDING = "pending"
    PLANNED = "planned"
    CODED = "coded"
    RENDERED = "rendered"
    FAILED = "failed"


def slugify(text: str) -> str:
    """Convert a title or topic string to a filesystem and URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "course"


class VisualGrammar(BaseModel):
    """Global visual theme and tokens shared across all lectures in a course."""
    theme_name: str = "academic_modern"
    primary_color: str = "BLUE_C"
    secondary_color: str = "YELLOW_C"
    accent_color: str = "TEAL_C"
    background_color: str = "BLACK"
    coordinate_style: str = "NumberPlane(x_range=[-7, 7, 1], y_range=[-4, 4, 1])"
    latex_font: str = "modern"
    style_guidelines: list[str] = Field(
        default_factory=lambda: [
            "Use primary color for main subjects and definitions.",
            "Use secondary color for dynamic transformations, vectors, or highlighted terms.",
            "Use accent color for annotations, braces, and arrows.",
            "Keep animations smooth and uncluttered with generous run_time pacing.",
        ]
    )


class LectureSpec(BaseModel):
    """Pedagogical blueprint and requirements for an individual lecture."""
    lecture_number: int = Field(..., ge=1, description="1-indexed sequence number")
    title: str = Field(..., min_length=2)
    description: str = Field(..., description="Abstract of lecture content and motivation")
    key_concepts: list[str] = Field(default_factory=list, description="Core concepts taught")
    prerequisites_from_course: list[str] = Field(
        default_factory=list,
        description="Concepts introduced in earlier lectures that this lecture builds on",
    )
    visual_goals: list[str] = Field(
        default_factory=list,
        description="Visual animations and geometric intuition to illustrate",
    )
    estimated_duration_minutes: float = Field(default=3.0, ge=0.5, le=30.0)


class CourseSyllabus(BaseModel):
    """Complete syllabus and curriculum specification for a multi-lecture course."""
    course_id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=2)
    slug: str = Field(default="")
    topic: str
    subject: str = "General"
    target_audience: Audience = Audience.EXPLORING
    overview: str = Field(..., description="High-level pedagogical thesis of the course")
    learning_outcomes: list[str] = Field(default_factory=list)
    visual_grammar: VisualGrammar = Field(default_factory=VisualGrammar)
    lectures: list[LectureSpec] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_and_populate_slug_and_numbers(self) -> "CourseSyllabus":
        if not self.slug:
            self.slug = slugify(self.title)
        # Ensure lectures are strictly numbered 1..N
        for idx, spec in enumerate(self.lectures, start=1):
            spec.lecture_number = idx
        return self


class Lecture(BaseModel):
    """Execution state and generated artifacts for an individual lecture."""
    lecture_id: UUID = Field(default_factory=uuid4)
    lecture_number: int
    spec: LectureSpec
    status: RenderStatus = RenderStatus.PENDING
    scene_plan: LessonPlan | None = None
    narration_plan: NarrationPlan | None = None
    final_code: FinalCode | None = None
    compile_result: CompileResult | None = None
    study_notes: str | None = None
    video_path: str | None = None
    error_message: str | None = None

    @property
    def is_rendered(self) -> bool:
        return self.status == RenderStatus.RENDERED and self.video_path is not None


class Course(BaseModel):
    """Top-level aggregate root for a complete multi-lecture course."""
    course_id: UUID = Field(default_factory=uuid4)
    title: str
    slug: str
    syllabus: CourseSyllabus
    lectures: list[Lecture] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    workspace_dir: str | None = None

    @classmethod
    def from_syllabus(cls, syllabus: CourseSyllabus, workspace_dir: Path | str | None = None) -> "Course":
        lectures = [
            Lecture(
                lecture_number=spec.lecture_number,
                spec=spec,
                status=RenderStatus.PENDING,
            )
            for spec in syllabus.lectures
        ]
        return cls(
            course_id=syllabus.course_id,
            title=syllabus.title,
            slug=syllabus.slug,
            syllabus=syllabus,
            lectures=lectures,
            workspace_dir=str(workspace_dir) if workspace_dir else None,
        )

    def get_lecture(self, lecture_number: int) -> Lecture | None:
        for lec in self.lectures:
            if lec.lecture_number == lecture_number:
                return lec
        return None

    @property
    def progress_summary(self) -> dict[str, int]:
        counts = {status.value: 0 for status in RenderStatus}
        for lec in self.lectures:
            counts[lec.status.value] += 1
        return counts


class CourseManifest(BaseModel):
    """Lightweight metadata file serialized at root of .educlaw/courses/<slug>/."""
    course_id: str
    title: str
    slug: str
    subject: str
    target_audience: str
    total_lectures: int
    rendered_lectures: int
    created_at: str
    updated_at: str
    lectures_summary: list[dict[str, Any]]

"""Agent factories for Course and Lecture series generation."""

from __future__ import annotations

from typing import Any
from uuid import uuid4
from pydantic_ai import Agent

from educlaw.animateworkflow.contracts import FinalCode, LessonPlan, NarrationPlan
from educlaw.courses.contracts import CourseSyllabus
from educlaw.courses.prompts import (
    CURRICULUM_ARCHITECT_INSTRUCTIONS,
    LECTURE_CODEGEN_INSTRUCTIONS,
    LECTURE_NARRATION_INSTRUCTIONS,
    LECTURE_NOTES_INSTRUCTIONS,
    LECTURE_SCENE_PLANNER_INSTRUCTIONS,
)
from educlaw.settings import Settings


def _default_test_syllabus() -> dict[str, Any]:
    return {
        "title": "Educational Course",
        "slug": "educational-course",
        "topic": "Fundamentals",
        "subject": "General",
        "target_audience": "exploring",
        "overview": "A comprehensive introductory series.",
        "learning_outcomes": ["Understand fundamental concepts", "Apply visual reasoning"],
        "visual_grammar": {},
        "lectures": [
            {
                "lecture_number": 1,
                "title": "Lecture 1: Foundations",
                "description": "Introduction and core principles.",
                "key_concepts": ["Foundations", "First principles"],
            },
            {
                "lecture_number": 2,
                "title": "Lecture 2: Core Mechanisms",
                "description": "Deep dive into dynamics.",
                "key_concepts": ["Transformations", "Properties"],
            },
            {
                "lecture_number": 3,
                "title": "Lecture 3: Synthesis & Applications",
                "description": "Advanced patterns and synthesis.",
                "key_concepts": ["Synthesis", "Applications"],
            },
        ],
    }


def _default_test_scene_plan() -> dict[str, Any]:
    return {
        "videos": [
            {
                "video_id": str(uuid4()),
                "title": "Lecture Animation",
                "duration_minutes": 2.0,
                "scenes": [
                    {
                        "scene_id": str(uuid4()),
                        "name": "intro_step",
                        "purpose": "hook",
                        "code": "self.play(Create(Circle()))",
                        "visual_description": "Animated circle presentation",
                        "objects": [{"name": "circle_1", "obj_type": "Circle", "properties": {}}],
                        "animations": [{"animation_type": "Create", "targets": ["circle_1"], "params": {}}],
                    }
                ],
            }
        ]
    }


def _default_test_narration_plan() -> dict[str, Any]:
    return {
        "steps": [
            {
                "scene_id": str(uuid4()),
                "narration": "Welcome to this lecture. Let us examine the core concepts.",
                "bookmarks": [],
                "duration": 3.0,
            }
        ]
    }


def _default_test_code() -> dict[str, Any]:
    return {
        "code": (
            "from manim import *\n"
            "from manim_voiceover import VoiceoverScene\n\n"
            "class LectureScene(VoiceoverScene):\n"
            "    def construct(self):\n"
            "        c = Circle()\n"
            "        self.play(Create(c))\n"
        ),
        "scene_name": "LectureScene",
    }


def _is_test_mode(settings: Settings | None, model: str | object | None) -> bool:
    if model == "test":
        return True
    if settings and settings.test_model:
        return True
    return False


def build_curriculum_agent(
    settings: Settings | None = None,
    *,
    model: str | object | None = None,
) -> Agent[object, CourseSyllabus]:
    """Build the Curriculum Architect Agent that plans complete course syllabi."""
    if _is_test_mode(settings, model):
        from pydantic_ai.models.test import TestModel
        resolved_model = TestModel(custom_output_args=_default_test_syllabus())
    elif model is not None:
        resolved_model = model
    elif settings and settings.model:
        resolved_model = settings.model
    else:
        resolved_model = "openrouter:openai/gpt-4o-mini"

    return Agent(
        model=resolved_model,
        name="CurriculumArchitectAgent",
        output_type=CourseSyllabus,
        instructions=CURRICULUM_ARCHITECT_INSTRUCTIONS,
    )


def build_lecture_scene_agent(
    settings: Settings | None = None,
    *,
    model: str | object | None = None,
) -> Agent[object, LessonPlan]:
    """Build the Lecture Scene Planner Agent for visual animation breakdowns."""
    if _is_test_mode(settings, model):
        from pydantic_ai.models.test import TestModel
        resolved_model = TestModel(custom_output_args=_default_test_scene_plan())
    elif model is not None:
        resolved_model = model
    elif settings and settings.model:
        resolved_model = settings.model
    else:
        resolved_model = "openrouter:openai/gpt-4o-mini"

    return Agent(
        model=resolved_model,
        name="LectureSceneAgent",
        output_type=LessonPlan,
        instructions=LECTURE_SCENE_PLANNER_INSTRUCTIONS,
    )


def build_lecture_narration_agent(
    settings: Settings | None = None,
    *,
    model: str | object | None = None,
) -> Agent[object, NarrationPlan]:
    """Build the Lecture Narration Agent for voiceover scriptwriting."""
    if _is_test_mode(settings, model):
        from pydantic_ai.models.test import TestModel
        resolved_model = TestModel(custom_output_args=_default_test_narration_plan())
    elif model is not None:
        resolved_model = model
    elif settings and settings.model:
        resolved_model = settings.model
    else:
        resolved_model = "openrouter:openai/gpt-4o-mini"

    return Agent(
        model=resolved_model,
        name="LectureNarrationAgent",
        output_type=NarrationPlan,
        instructions=LECTURE_NARRATION_INSTRUCTIONS,
    )


def build_lecture_code_agent(
    settings: Settings | None = None,
    *,
    model: str | object | None = None,
) -> Agent[object, FinalCode]:
    """Build the Lecture Code Generator Agent for Python Manim scripts."""
    if _is_test_mode(settings, model):
        from pydantic_ai.models.test import TestModel
        resolved_model = TestModel(custom_output_args=_default_test_code())
    elif model is not None:
        resolved_model = model
    elif settings and settings.model:
        resolved_model = settings.model
    else:
        resolved_model = "openrouter:openai/gpt-4o-mini"

    return Agent(
        model=resolved_model,
        name="LectureCodeAgent",
        output_type=FinalCode,
        instructions=LECTURE_CODEGEN_INSTRUCTIONS,
    )


def build_lecture_notes_agent(
    settings: Settings | None = None,
    *,
    model: str | object | None = None,
) -> Agent[object, str]:
    """Build the Lecture Companion Notes Agent for Markdown study guides."""
    if _is_test_mode(settings, model):
        from pydantic_ai.models.test import TestModel
        resolved_model = TestModel(custom_output_text="# Lecture Study Guide\n\n## Key Concepts\n- Fundamentals\n- Intuition\n\n## Quiz\n1. What is the core theorem?")
    elif model is not None:
        resolved_model = model
    elif settings and settings.model:
        resolved_model = settings.model
    else:
        resolved_model = "openrouter:openai/gpt-4o-mini"

    return Agent(
        model=resolved_model,
        name="LectureNotesAgent",
        output_type=str,
        instructions=LECTURE_NOTES_INSTRUCTIONS,
    )

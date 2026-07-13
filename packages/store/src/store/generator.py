"""Builds a schema-valid (but mock) ir.LectureIR for a topic/subject/duration.
Stands in for the real apps/agents planner pipeline, which isn't wired up yet.
Swap the body of `build_lecture_ir` for a real pipeline call when that lands;
callers (CLI/TUI, via generator.create_lecture/create_course) don't need to change.
"""
from __future__ import annotations

import re
from datetime import datetime
from uuid import uuid4

from ir import (
    AmbientAnimation,
    Beat,
    EndingScene,
    EntityType,
    Lecture,
    LectureIR,
    NarrationSegment,
    Operation,
    OperationType,
    Scene,
    SceneObject,
    Storyboard,
    StoryboardMove,
    StoryboardStep,
    Subject,
)

VALID_SUBJECTS = {s.value for s in Subject}


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "topic"


def new_id(topic: str) -> str:
    return f"{slugify(topic)}-{uuid4().hex[:6]}"


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def normalize_subject(subject: str) -> str:
    s = subject.strip().lower()
    return s if s in VALID_SUBJECTS else Subject.MATH.value


def build_lecture_ir(topic: str, subject: str, duration_minutes: float, query: str) -> LectureIR:
    subj = Subject(normalize_subject(subject))

    lecture = Lecture(
        topic=topic,
        subject=subj,
        greeting=f"{_greeting()}! Let's talk about {topic}.",
        assumptions=[f"You already have a working sense of the basics of {subj.value}."],
        objectives=[f"Understand what {topic} is and why it matters."],
        opener=(
            f"Most people jump straight to advanced {subj.value} without pausing "
            f"on {topic} — let's fix that."
        ),
        learning_outcomes=[f"Explain {topic} in your own words."],
    )

    scene = Scene(
        id="s1",
        title=topic,
        scene_graph=[
            SceneObject(id="title", entity_type=EntityType.TITLE, params={"text": topic}),
            SceneObject(id="circle", entity_type=EntityType.CIRCLE, params={"radius": 1.5}),
            SceneObject(
                id="eq",
                entity_type=EntityType.MATH_TEX,
                params={"tex": f"\\text{{{topic}}}"},
            ),
        ],
        beats=[
            Beat(
                animation_segment=[
                    Operation(target="title", op=OperationType.CREATE, run_time=1.5)
                ],
                narration=NarrationSegment(text=lecture.opener),
                hold_seconds=1.0,
                ambient=[AmbientAnimation(type="breathe")],
            ),
            Beat(
                animation_segment=[
                    Operation(target="circle", op=OperationType.FADE_IN, run_time=1.5)
                ],
                narration=NarrationSegment(
                    text=f"Here's a simple picture of {topic} to anchor the idea."
                ),
                hold_seconds=1.0,
                ambient=[AmbientAnimation(type="glow_pulse", target="circle")],
            ),
            Beat(
                animation_segment=[
                    Operation(target="eq", op=OperationType.WRITE, run_time=1.5)
                ],
                narration=NarrationSegment(
                    text=f"This captures the core idea behind {topic} in {subj.value}."
                ),
                hold_seconds=1.0,
            ),
            Beat(
                animation_segment=[
                    Operation(target="title", op=OperationType.REMOVE, run_time=0.0),
                    Operation(target="circle", op=OperationType.REMOVE, run_time=0.0),
                    Operation(target="eq", op=OperationType.REMOVE, run_time=0.0),
                ],
                narration=NarrationSegment(
                    text=f"That's {topic}. Next, explore related ideas in {subj.value}."
                ),
                hold_seconds=0.5,
            ),
        ],
    )

    storyboard = Storyboard(
        goal=f"Introduce {topic}",
        steps=[
            StoryboardStep(move=StoryboardMove.HOOK, goal=lecture.opener, scene_id="s1"),
            StoryboardStep(move=StoryboardMove.EXAMPLE, goal=f"Show {topic}", scene_id="s1"),
            StoryboardStep(move=StoryboardMove.SUMMARIZE, goal="Recap and close", scene_id="s1"),
        ],
    )

    return LectureIR(
        duration_target_seconds=duration_minutes * 60,
        lecture=lecture,
        storyboard=storyboard,
        scenes=[scene],
        ending=EndingScene(
            closer=f"Thanks for learning about {topic} with AOS.",
            suggested_next_topics=[f"A follow-up on {topic}"],
        ),
    )

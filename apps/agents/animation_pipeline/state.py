"""Typed state models for the Animation Pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from coder_run import CoderRunResult
from ir.manim_ir import Classification, Lecture
from teaching_script import TeachingScript


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

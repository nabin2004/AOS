"""HITL Skills package using Pydantic AI Harness Skills.

Loads Agent Skills (https://agentskills.io/specification) from the safe local
skills directory (app/skills/) using `pydantic_ai_harness.Skills`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from pydantic_ai_harness import Skills

SKILLS_DIR = Path(__file__).resolve().parent


def get_skills(
    *,
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
) -> Skills:
    """Create a Skills capability instance pointing to the local safe skills library."""
    if include is not None:
        return Skills(SKILLS_DIR, include=include)
    if exclude is not None:
        return Skills(SKILLS_DIR, exclude=exclude)
    return Skills(SKILLS_DIR)


def get_composer_skills() -> Skills:
    """Get Skills capability for Composer Agent (manim-composer)."""
    return Skills(SKILLS_DIR, include=["manim-composer"])


def get_coder_skills() -> Skills:
    """Get Skills capability for Coder Agent (manimce-best-practices, manim-render)."""
    return Skills(SKILLS_DIR, include=["manimce-best-practices", "manim-render"])


def get_repair_skills() -> Skills:
    """Get Skills capability for Repair Agent (manimce-best-practices, manim-render)."""
    return Skills(SKILLS_DIR, include=["manimce-best-practices", "manim-render"])


__all__ = [
    "SKILLS_DIR",
    "Skills",
    "get_skills",
    "get_composer_skills",
    "get_coder_skills",
    "get_repair_skills",
]

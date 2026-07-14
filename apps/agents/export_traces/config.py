from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

SCHEMA_VERSION = 1

DEFAULT_REGION = "eu"
DEFAULT_DAYS = 30
DEFAULT_PAGE_SIZE = 10_000
VALIDATION_FEEDBACK_PREFIX = "Validation feedback:"


class FinalOutputMode(str, Enum):
    """How to extract the assistant target for final_answer SFT rows."""

    JSON = "json"
    SOURCE = "source"
    TEXT = "text"


@dataclass(frozen=True)
class AgentProfile:
    name: str
    final_output_mode: FinalOutputMode
    source_field: str | None = None


# Per-agent rules for final_answer conversion (all graph agents).
AGENT_PROFILES: dict[str, AgentProfile] = {
    "Classifier Agent": AgentProfile("Classifier Agent", FinalOutputMode.JSON),
    "Lecture Planner Agent": AgentProfile("Lecture Planner Agent", FinalOutputMode.JSON),
    "Storyboard Planner Agent": AgentProfile("Storyboard Planner Agent", FinalOutputMode.JSON),
    "Scene Planner Agent": AgentProfile("Scene Planner Agent", FinalOutputMode.JSON),
    "Beat Planner Agent": AgentProfile("Beat Planner Agent", FinalOutputMode.JSON),
    "Narration Planner Agent": AgentProfile("Narration Planner Agent", FinalOutputMode.JSON),
    "Manim Code Writer": AgentProfile(
        "Manim Code Writer", FinalOutputMode.SOURCE, source_field="source"
    ),
    "Code Agent": AgentProfile("Code Agent", FinalOutputMode.TEXT),
    "Inspector Agent": AgentProfile("Inspector Agent", FinalOutputMode.JSON),
    "Validation Agent": AgentProfile("Validation Agent", FinalOutputMode.JSON),
    "Repair Agent": AgentProfile("Repair Agent", FinalOutputMode.JSON),
    "Narrator Agent": AgentProfile("Narrator Agent", FinalOutputMode.TEXT),
}

DEFAULT_AGENT_PROFILE = AgentProfile("Unknown Agent", FinalOutputMode.JSON)

SFTFormat = Literal["final_answer", "tool_trace", "both"]

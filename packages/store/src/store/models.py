from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LectureRecord(BaseModel):
    id: str
    kind: Literal["lecture"] = "lecture"
    query: str
    topic: str
    subject: str
    duration_minutes: float
    created_at: str = Field(default_factory=utcnow_iso)
    course_id: Optional[str] = None
    episode_index: Optional[int] = None
    ir: dict[str, Any]


class CourseRecord(BaseModel):
    id: str
    kind: Literal["course"] = "course"
    query: str
    topic: str
    subject: str
    duration_minutes: float
    total_episodes: int
    created_at: str = Field(default_factory=utcnow_iso)
    episode_ids: list[str] = Field(default_factory=list)

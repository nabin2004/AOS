"""Pydantic schemas for the Human-in-the-Loop Animation Critique & Review System."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class CritiqueCategory(str, Enum):
    POSITIONING = "positioning"
    VISUAL_DRIFT = "visual_drift"
    VISIBILITY = "visibility"
    ANIMATION = "animation"
    TIMING = "timing"
    SCIENTIFIC_ACCURACY = "scientific_accuracy"
    EXPLANATION = "explanation"
    NARRATION = "narration"
    GENERAL = "general"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SpatialCorrection(BaseModel):
    action: str = Field(..., description="Action: move, scale, reposition, hide, make_larger, fix_overlap")
    target_object: str = Field(..., description="Name of the targeted mobject")
    old_position: tuple[float, float] | None = None
    new_position: tuple[float, float] | None = None
    old_scale: float | None = None
    new_scale: float | None = None


class CritiqueSubmissionRequest(BaseModel):
    video_generation_id: str = Field(..., description="ID of the video being critiqued")
    revision: int = Field(1, ge=1, description="Current revision number being reviewed")
    category: CritiqueCategory = Field(..., description="Primary failure category")
    feedback: str = Field(..., min_length=1, max_length=2000, description="User critique or issue description")
    timestamp_seconds: float | None = Field(None, ge=0.0, description="Video timestamp where problem was observed")
    target_object: str | None = Field(None, max_length=100, description="Specific mobject or element name")
    severity: SeverityLevel = Field(SeverityLevel.MEDIUM, description="Critique urgency / severity")
    session_id: str | None = Field(None, description="Active chat conversation or session ID")
    manim_code: str | None = Field(None, description="Manim code of the revision being critiqued")
    spatial_correction: SpatialCorrection | None = Field(None, description="Structured spatial/bounding box adjustment")


class CritiqueRecord(BaseModel):
    critique_id: str
    video_generation_id: str
    revision: int
    category: CritiqueCategory
    feedback: str
    timestamp_seconds: float | None = None
    target_object: str | None = None
    severity: SeverityLevel = SeverityLevel.MEDIUM
    session_id: str | None = None
    created_at: datetime
    spatial_correction: SpatialCorrection | None = None
    repair_prompt: str | None = None
    status: Literal["pending", "repairing", "completed", "rejected"] = "pending"
    repaired_video_id: str | None = None
    accepted: bool = False


class CritiqueSubmissionResponse(BaseModel):
    success: bool
    critique_id: str
    video_generation_id: str
    revision: int
    category: CritiqueCategory
    message: str
    repair_instructions: str
    suggested_action: str


class AcceptRevisionRequest(BaseModel):
    video_generation_id: str
    revision: int
    rating: int | None = Field(5, ge=1, le=5)
    notes: str | None = None


class AcceptRevisionResponse(BaseModel):
    success: bool
    video_generation_id: str
    revision: int
    message: str
    dataset_logged: bool


class VideoRevision(BaseModel):
    revision: int
    video_generation_id: str
    stream_url: str
    prompt: str | None = None
    code: str | None = None
    critique_tags: list[str] = []
    accepted: bool = False
    created_at: datetime


class RevisionHistoryResponse(BaseModel):
    video_generation_id: str
    active_revision: int
    revisions: list[VideoRevision]

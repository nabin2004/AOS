"""API endpoints for human visual critique, review taxonomy, and revision acceptance."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.schemas.critique import (
    AcceptRevisionRequest,
    AcceptRevisionResponse,
    CritiqueSubmissionRequest,
    CritiqueSubmissionResponse,
    RevisionHistoryResponse,
)
from app.services.critique_recorder import CritiqueRecorder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["animation-critique"])


@router.post("/{video_id}/critique", response_model=CritiqueSubmissionResponse)
async def submit_critique(
    video_id: str,
    payload: CritiqueSubmissionRequest,
) -> dict[str, Any]:
    """Submit a structured visual critique (positioning, visual drift, scientific accuracy, etc.)."""
    if payload.video_generation_id != video_id:
        payload.video_generation_id = video_id

    try:
        record = CritiqueRecorder.record_critique(payload)
        return {
            "success": True,
            "critique_id": record.critique_id,
            "video_generation_id": video_id,
            "revision": payload.revision,
            "category": payload.category,
            "message": (
                f"Critique for {payload.category.value.replace('_', ' ')} recorded successfully. "
                "Agent repair dispatched."
            ),
            "repair_instructions": record.repair_prompt or "",
            "suggested_action": f"Repairing {payload.category.value} in Manim code...",
        }
    except Exception as exc:
        logger.exception("Failed to record critique for video %s: %s", video_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record critique: {exc}",
        ) from exc


@router.get("/{video_id}/revisions", response_model=RevisionHistoryResponse)
async def get_revisions(video_id: str) -> dict[str, Any]:
    """Get the revision history tree and critique tags for a video."""
    revisions = CritiqueRecorder.get_revisions(video_id)
    active_rev = max((r.revision for r in revisions), default=1)
    return {
        "video_generation_id": video_id,
        "active_revision": active_rev,
        "revisions": revisions,
    }


@router.post("/{video_id}/accept", response_model=AcceptRevisionResponse)
async def accept_revision(
    video_id: str,
    payload: AcceptRevisionRequest,
) -> dict[str, Any]:
    """Accept the current revision as final and log as a chosen trajectory."""
    if payload.video_generation_id != video_id:
        payload.video_generation_id = video_id

    logged = CritiqueRecorder.mark_accepted(payload)
    return {
        "success": True,
        "video_generation_id": video_id,
        "revision": payload.revision,
        "message": f"Revision {payload.revision} accepted as verified final output.",
        "dataset_logged": logged,
    }

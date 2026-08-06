"""Video generation list / get / stream endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, VideoGenerationSvc
from app.core.exceptions import NotFoundError
from app.schemas.video_generation import VideoGenerationList, VideoGenerationRead

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=VideoGenerationList)
async def list_videos(
    service: VideoGenerationSvc,
    user: CurrentUser,
    conversation_id: UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> Any:
    """List video generations for the current user (optionally filtered by conversation)."""
    return await service.list_for_user(
        user.id,
        conversation_id=conversation_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{video_id}", response_model=VideoGenerationRead)
async def get_video(
    video_id: UUID,
    service: VideoGenerationSvc,
    user: CurrentUser,
) -> Any:
    row = await service.get_for_user(video_id, user.id)
    return VideoGenerationRead.model_validate(row)


@router.get("/{video_id}/stream", response_model=None)
async def stream_video(
    video_id: UUID,
    service: VideoGenerationSvc,
    user: CurrentUser,
) -> Any:
    """Auth-gated proxy stream from MinIO (inline for Video.js)."""
    try:
        row = await service.get_for_user(video_id, user.id)
        body = service.open_stream_for(row)
    except NotFoundError:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found") from None

    headers = {
        "Content-Disposition": f'inline; filename="{video_id}.mp4"',
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=3600",
    }
    return StreamingResponse(body, media_type="video/mp4", headers=headers)

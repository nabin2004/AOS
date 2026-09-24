"""Video generation list / get / stream endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, VideoGenerationSvc
from app.core.exceptions import NotFoundError
from app.schemas.video_generation import VideoGenerationList, VideoGenerationRead

router = APIRouter(prefix="/videos", tags=["videos"])
logger = logging.getLogger(__name__)


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
    request: Request,
    service: VideoGenerationSvc,
    user: CurrentUser,
) -> Any:
    """Auth-gated proxy stream from MinIO with full byte-range support."""
    try:
        row = await service.get_for_user(video_id, user.id)
        range_header = request.headers.get("range")
        body, status_code, headers = service.open_stream_for(row, range_header=range_header)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found") from None

    headers["Content-Disposition"] = f'inline; filename="{video_id}.mp4"'
    return StreamingResponse(body, status_code=status_code, media_type="video/mp4", headers=headers)


@router.get("/{video_id}/slides/{slide_num}/stream", response_model=None)
async def stream_slide_video(
    video_id: UUID,
    slide_num: int,
    request: Request,
    service: VideoGenerationSvc,
    user: CurrentUser,
) -> Any:
    """Auth-gated proxy stream for an individual slide/teaching segment MP4 with byte-range support."""
    try:
        row = await service.get_for_user(video_id, user.id)
        range_header = request.headers.get("range")
        body, status_code, headers = service.open_slide_stream_for(row, slide_num, range_header=range_header)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Slide {slide_num} not found") from None

    headers["Content-Disposition"] = f'inline; filename="{video_id}_slide_{slide_num}.mp4"'
    return StreamingResponse(body, status_code=status_code, media_type="video/mp4", headers=headers)


@router.get("/{video_id}/code", response_model=None)
async def get_video_code(
    video_id: UUID,
    service: VideoGenerationSvc,
    user: CurrentUser,
) -> Any:
    """Auth-gated proxy stream of the generated Manim / Python scene source code."""
    try:
        row = await service.get_for_user(video_id, user.id)
        body = service.open_code_stream_for(row)
    except NotFoundError:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene code not found") from None

    headers = {
        "Content-Disposition": f'inline; filename="{video_id}.py"',
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "private, max-age=3600",
    }
    return StreamingResponse(body, media_type="text/plain; charset=utf-8", headers=headers)


@router.post("/classify", response_model=None)
async def classify_text(
    payload: dict[str, Any],
) -> Any:
    """Classify educational text for Manim visual animatability."""
    from app.services.manim_studio import classify_text_for_manim
    text = payload.get("text", "")
    model_name = payload.get("model_name")
    base_url = payload.get("base_url")
    api_key = payload.get("api_key")
    return await classify_text_for_manim(
        text, model_name=model_name, base_url=base_url, api_key=api_key
    )


@router.post("/plan", response_model=None)
async def compose_plan(
    payload: dict[str, Any],
    user: CurrentUser,
) -> Any:
    """Generate a structured scenes.md visual plan using manim-composer skills."""
    from app.services.manim_studio import compose_plan_service
    text = payload.get("text", "")
    hints = payload.get("hints")
    model_name = payload.get("model_name")
    base_url = payload.get("base_url")
    api_key = payload.get("api_key")
    return await compose_plan_service(
        text,
        hints=hints,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
    )


@router.post("/plan/stream", response_model=None)
async def compose_plan_stream(
    payload: dict[str, Any],
    user: CurrentUser,
) -> Any:
    """Stream Manim Composer's `scenes.md` draft as SSE token deltas."""
    from app.services.manim_studio import compose_plan_stream_service

    return StreamingResponse(
        compose_plan_stream_service(
            payload.get("text", ""),
            hints=payload.get("hints"),
            model_name=payload.get("model_name"),
            base_url=payload.get("base_url"),
            api_key=payload.get("api_key"),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/code", response_model=None)
async def synthesize_code(
    payload: dict[str, Any],
    user: CurrentUser,
) -> Any:
    """Synthesize Manim Community code using manimce-best-practices skills."""
    from app.services.manim_studio import synthesize_code_service
    plan = payload.get("plan", "")
    knowledge_text = payload.get("knowledge_text")
    scene_name = payload.get("scene_name")
    model_name = payload.get("model_name")
    base_url = payload.get("base_url")
    api_key = payload.get("api_key")
    repair_error = payload.get("repair_error")
    return await synthesize_code_service(
        plan,
        knowledge_text=knowledge_text,
        scene_name=scene_name,
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        repair_error=repair_error,
    )


@router.post("/repair", response_model=None)
async def repair_code(
    payload: dict[str, Any],
    user: CurrentUser,
) -> Any:
    """Repair the submitted Manim source against a concrete compiler traceback."""
    from app.services.manim_studio import repair_code_service

    return await repair_code_service(
        code=payload.get("code", ""),
        error=payload.get("error", ""),
        scene_name=payload.get("scene_name"),
        model_name=payload.get("model_name"),
        base_url=payload.get("base_url"),
        api_key=payload.get("api_key"),
    )


@router.post("/code/stream", response_model=None)
async def synthesize_code_stream(
    payload: dict[str, Any],
    user: CurrentUser,
) -> Any:
    """Stream ManimCE Coder output as SSE token deltas."""
    from app.services.manim_studio import synthesize_code_stream_service

    return StreamingResponse(
        synthesize_code_stream_service(
            payload.get("plan", ""),
            knowledge_text=payload.get("knowledge_text"),
            scene_name=payload.get("scene_name"),
            model_name=payload.get("model_name"),
            base_url=payload.get("base_url"),
            api_key=payload.get("api_key"),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/render-custom", response_model=None)
async def render_custom_scene(
    payload: dict[str, Any],
    user: CurrentUser,
    request: Request,
) -> Any:
    """Compile and render custom Manim scene code with quality options."""
    from app.db.session import get_db_context
    from app.services.manim_studio import render_custom_code_service
    code = payload.get("code", "")
    scene_name = payload.get("scene_name")
    quality = payload.get("quality", "l")
    prompt = payload.get("prompt")
    conversation_id_raw = payload.get("conversation_id")
    conv_id = UUID(conversation_id_raw) if conversation_id_raw else None
    skip_preflight = bool(payload.get("skip_preflight", False))

    async with get_db_context() as db:
        try:
            return await render_custom_code_service(
                code=code,
                scene_name=scene_name,
                quality=quality,
                user_id=user.id,
                db=db,
                conversation_id=conv_id,
                prompt=prompt,
                skip_preflight=skip_preflight,
            )
        except HTTPException:
            # The renderer returns a 4xx exception containing the Manim stderr
            # when compilation fails. Preserve it so the Studio can show the
            # actionable compiler log rather than a generic server error.
            raise
        except Exception as exc:
            logger.exception("Unexpected custom Manim render failure")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Render execution failed: {exc!s}",
            ) from exc


@router.post("/preflight", response_model=None)
async def preflight_check(
    payload: dict[str, Any],
    user: CurrentUser,
) -> Any:
    """Run static preflight analysis on Manim code without rendering."""
    from app.services.manim_code import preflight_manim_code, repair_manim_code

    code = payload.get("code", "")
    repaired = repair_manim_code(code)
    preflight = preflight_manim_code(repaired.code)
    has_blocking = any(item.get("blocking", False) or item.get("severity", "error") == "error" for item in preflight.errors)

    return {
        "valid": preflight.valid and not has_blocking,
        "status": "safe" if not preflight.errors else ("failed" if has_blocking else "warning"),
        "blocking": has_blocking,
        "errors": list(preflight.errors),
        "issues": list(preflight.issues or preflight.errors),
        "repair_changes": list(repaired.changes),
        "repaired_code": repaired.code if repaired.changes else None,
    }


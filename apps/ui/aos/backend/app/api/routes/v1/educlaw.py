import sys
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException

# Ensure apps/educlaw is discoverable on sys.path
educlaw_path = Path(__file__).resolve().parents[6] / "educlaw"
if educlaw_path.is_dir() and str(educlaw_path) not in sys.path:
    sys.path.insert(0, str(educlaw_path))

from app.api.deps import CurrentUser
from app.services.educlaw_service import EduClawService

router = APIRouter(prefix="/educlaw", tags=["educlaw"])


@router.get("/memory")
async def get_memory_graph(
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Retrieve the Dagestan memory graph for the current workspace."""
    service = EduClawService()
    return await service.get_memory_graph()


@router.post("/memory/curate")
async def curate_memory(
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Trigger memory consolidation and curation."""
    service = EduClawService()
    res = await service.curate_memory()
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error", "Memory curation failed"))
    return res


@router.get("/config")
async def get_educlaw_config(
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Get active EduClaw harness configuration and settings."""
    from educlaw.settings import Settings
    settings = Settings.from_env()
    return {
        "model": settings.model,
        "permission_mode": settings.permission_mode,
        "manim_image": settings.manim_image,
        "manim_quality": settings.manim_quality,
        "context_window_tokens": settings.context_window_tokens,
        "compaction_threshold": settings.compaction_threshold,
        "kitaru": settings.kitaru,
    }

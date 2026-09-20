"""System logs API endpoints for real-time diagnostic visualization and debugging."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.log_buffer import LogEntry, log_buffer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system-logs"])


@router.get("/logs")
async def get_system_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    level: str | None = Query(default=None),
    query: str | None = Query(default=None),
    since_id: int | None = Query(default=None),
) -> dict[str, Any]:
    """Retrieve buffered structured application logs for debugging and telemetry."""
    entries = log_buffer.query(
        limit=limit,
        level=level,
        query=query,
        since_id=since_id,
    )
    return {
        "total": len(entries),
        "logs": [e.model_dump() for e in entries],
        "logfire_project_url": "https://logfire-eu.pydantic.dev/nabinoli2004/aos",
        "service_name": settings.LOGFIRE_SERVICE_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.delete("/logs")
async def clear_system_logs() -> dict[str, str]:
    """Clear in-memory ring buffer logs."""
    log_buffer.clear()
    return {"status": "cleared"}


@router.websocket("/logs/stream")
async def stream_system_logs(websocket: WebSocket) -> None:
    """Stream real-time structured application logs over WebSocket for the UI Dev HUD."""
    await websocket.accept()
    queue = log_buffer.subscribe()

    try:
        # Send initial recent batch
        recent = log_buffer.query(limit=50)
        for entry in recent:
            await websocket.send_text(entry.model_dump_json())

        # Stream new entries as they arrive
        while True:
            entry = await queue.get()
            await websocket.send_text(entry.model_dump_json())
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        log_buffer.unsubscribe(queue)

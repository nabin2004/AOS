"""Celery tasks for Manim video generation (subprocess into apps/agents)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from celery import shared_task

from app.core.config import settings
from app.db.session import get_worker_db_context

logger = logging.getLogger(__name__)

VIDEO_STATUS_CHANNEL = "video_status"

# Lecture pipelines can run a long time (IR + Docker Manim + ffmpeg).
_SOFT_LIMIT = 50 * 60
_HARD_LIMIT = 60 * 60


def _resolve_agents_dir() -> Path:
    if settings.AGENTS_DIR:
        return Path(settings.AGENTS_DIR).resolve()
    # backend/app/worker/tasks/video_tasks.py → apps/agents
    here = Path(__file__).resolve()
    candidates = [
        here.parents[6] / "agents",  # .../apps/ui/aos/backend/app/worker/tasks → apps
        here.parents[5] / "agents",
        Path.cwd().parent.parent.parent / "agents",
        Path.cwd() / "apps" / "agents",
    ]
    for path in candidates:
        if (path / "cli.py").is_file():
            return path.resolve()
    raise FileNotFoundError(
        "Could not locate apps/agents (cli.py). Set AGENTS_DIR in the backend .env."
    )


def _run_agents_cli(mode: str, prompt: str) -> dict[str, Any]:
    """Invoke ``cli.py animate|generate --json`` and parse the VideoArtifact."""
    agents_dir = _resolve_agents_dir()
    command = "animate" if mode == "animate" else "generate"
    cmd = [
        settings.AGENTS_UV_CMD,
        "run",
        "python",
        "cli.py",
        command,
        prompt,
        "--json",
        "--no-banner",
    ]
    if mode == "animate":
        cmd.append("--fast")

    logger.info("Running agents CLI in %s: %s …", agents_dir, command)
    env = os.environ.copy()
    proc = subprocess.run(
        cmd,
        cwd=str(agents_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if stderr:
        logger.info("agents stderr (tail): %s", stderr[-2000:])

    # Prefer the last non-empty line that parses as JSON
    artifact: dict[str, Any] | None = None
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            artifact = json.loads(line)
            break
        except json.JSONDecodeError:
            continue

    if artifact is None:
        return {
            "ok": False,
            "mode": mode,
            "video_path": None,
            "run_dir": None,
            "error": (
                f"agents CLI returned no JSON (exit={proc.returncode}): "
                f"{stderr[-500:] or stdout[-500:] or 'empty output'}"
            ),
            "detail": {},
        }
    return artifact


async def _notify_video_status(payload: dict[str, Any]) -> None:
    try:
        r = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )  # type: ignore[no-untyped-call]
        await r.publish(VIDEO_STATUS_CHANNEL, json.dumps(payload, default=str))
        await r.aclose()
    except Exception as exc:
        logger.warning("Failed to publish video_status: %s", exc)


async def _persist_assistant_result(
    *,
    conversation_id: UUID,
    generation_id: UUID,
    mode: str,
    ok: bool,
    minio_key: str | None,
    error: str | None,
) -> UUID | None:
    """Persist assistant message + generate_video tool call; return message id."""
    from datetime import UTC, datetime

    from app.schemas.conversation import MessageCreate, ToolCallComplete, ToolCallCreate
    from app.services.conversation import ConversationService

    if ok:
        content = f"Your {mode} video is ready."
        tool_result = json.dumps(
            {
                "kind": "video",
                "video_generation_id": str(generation_id),
                "minio_key": minio_key,
                "mode": mode,
                "status": "completed",
            }
        )
        success = True
    else:
        content = f"Video generation failed: {error or 'unknown error'}"
        tool_result = json.dumps(
            {
                "kind": "video",
                "video_generation_id": str(generation_id),
                "mode": mode,
                "status": "failed",
                "error": error,
            }
        )
        success = False

    async with get_worker_db_context() as db:
        conv = ConversationService(db)
        msg = await conv.add_message(
            conversation_id,
            MessageCreate(role="assistant", content=content, model_name="manim-pipeline"),
        )
        tc = await conv.start_tool_call(
            msg.id,
            ToolCallCreate(
                tool_call_id=f"generate_video_{generation_id}",
                tool_name="generate_video",
                args={"mode": mode, "video_generation_id": str(generation_id)},
                started_at=datetime.now(UTC),
            ),
        )
        await conv.complete_tool_call(
            tc.id,
            ToolCallComplete(
                result=tool_result,
                completed_at=datetime.now(UTC),
                success=success,
            ),
        )
        return msg.id


async def _run_generate_video(generation_id: str) -> dict[str, Any]:
    from app.services.video_generation import VideoGenerationService
    from app.services.video_storage import get_video_storage

    gid = UUID(generation_id)

    async with get_worker_db_context() as db:
        svc = VideoGenerationService(db)
        row = await svc.mark_running(gid)
        mode = row.mode
        prompt = row.prompt
        user_id = row.user_id
        conversation_id = row.conversation_id
        object_key = svc.build_object_key(row)

    await _notify_video_status(
        {
            "type": "video_status",
            "video_generation_id": generation_id,
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
            "status": "running",
            "mode": mode,
        }
    )

    artifact = await asyncio.to_thread(_run_agents_cli, mode, prompt)
    run_dir = artifact.get("run_dir")

    if not artifact.get("ok") or not artifact.get("video_path"):
        error = artifact.get("error") or "video_pipeline_failed"
        assistant_id = await _persist_assistant_result(
            conversation_id=conversation_id,
            generation_id=gid,
            mode=mode,
            ok=False,
            minio_key=None,
            error=error,
        )
        async with get_worker_db_context() as db:
            await VideoGenerationService(db).mark_failed(
                gid,
                error_message=error,
                run_dir=run_dir,
                assistant_message_id=assistant_id,
            )
        await _notify_video_status(
            {
                "type": "video_status",
                "video_generation_id": generation_id,
                "conversation_id": str(conversation_id),
                "user_id": str(user_id),
                "status": "failed",
                "mode": mode,
                "error": error,
            }
        )
        return {"status": "failed", "error": error}

    video_path = artifact["video_path"]
    try:
        storage = get_video_storage()
        storage.upload_file(video_path, object_key)
    except Exception as exc:
        error = f"minio_upload_failed: {exc}"
        logger.exception("MinIO upload failed for %s", generation_id)
        assistant_id = await _persist_assistant_result(
            conversation_id=conversation_id,
            generation_id=gid,
            mode=mode,
            ok=False,
            minio_key=None,
            error=error,
        )
        async with get_worker_db_context() as db:
            await VideoGenerationService(db).mark_failed(
                gid,
                error_message=error,
                run_dir=run_dir,
                assistant_message_id=assistant_id,
            )
        await _notify_video_status(
            {
                "type": "video_status",
                "video_generation_id": generation_id,
                "conversation_id": str(conversation_id),
                "user_id": str(user_id),
                "status": "failed",
                "mode": mode,
                "error": error,
            }
        )
        return {"status": "failed", "error": error}

    assistant_id = await _persist_assistant_result(
        conversation_id=conversation_id,
        generation_id=gid,
        mode=mode,
        ok=True,
        minio_key=object_key,
        error=None,
    )
    async with get_worker_db_context() as db:
        await VideoGenerationService(db).mark_completed(
            gid,
            minio_key=object_key,
            run_dir=run_dir,
            assistant_message_id=assistant_id,
        )

    await _notify_video_status(
        {
            "type": "video_status",
            "video_generation_id": generation_id,
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
            "status": "completed",
            "mode": mode,
            "minio_key": object_key,
            "assistant_message_id": str(assistant_id) if assistant_id else None,
        }
    )
    return {"status": "completed", "minio_key": object_key}


@shared_task(
    bind=True,
    max_retries=0,
    soft_time_limit=_SOFT_LIMIT,
    time_limit=_HARD_LIMIT,
)  # type: ignore[misc]
def generate_video_task(self: Any, generation_id: str) -> dict[str, Any]:
    """Run Manim pipeline via agents CLI, upload MP4 to MinIO, update DB."""
    logger.info("generate_video_task start: %s", generation_id)
    try:
        return asyncio.run(_run_generate_video(generation_id))
    except Exception as exc:
        logger.exception("generate_video_task failed: %s", generation_id)
        try:
            asyncio.run(
                _fail_hard(generation_id, str(exc))
            )
        except Exception:
            logger.exception("Failed to mark video generation failed after crash")
        raise


async def _fail_hard(generation_id: str, error: str) -> None:
    from app.repositories import video_generation as video_repo
    from app.services.video_generation import VideoGenerationService

    gid = UUID(generation_id)
    async with get_worker_db_context() as db:
        svc = VideoGenerationService(db)
        row = await video_repo.get_by_id(db, gid)
        if row is None:
            return
        await svc.mark_failed(gid, error_message=error)
        await _notify_video_status(
            {
                "type": "video_status",
                "video_generation_id": generation_id,
                "conversation_id": str(row.conversation_id),
                "user_id": str(row.user_id),
                "status": "failed",
                "mode": row.mode,
                "error": error,
            }
        )

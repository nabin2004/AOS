"""Celery tasks for Manim video generation (subprocess into apps/agents)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

import redis
import redis.asyncio as aioredis
from celery import shared_task

from app.core.config import settings
from app.db.session import get_worker_db_context

logger = logging.getLogger(__name__)

VIDEO_STATUS_CHANNEL = "video_status"

# Lecture pipelines can run a long time (IR + Docker Manim + ffmpeg).
_SOFT_LIMIT = 50 * 60
_HARD_LIMIT = 60 * 60

# Agents CLI prints ``-> {node_id}`` (Rich may wrap with ANSI); strip and map.
_NODE_PROGRESS_RE = re.compile(r"->\s*([A-Za-z0-9_]+)")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

_STAGE_MESSAGES: dict[str, str] = {
    "ClassifyNode": "Classifying topic…",
    "PlanLectureNode": "Planning the lecture…",
    "CodeAgent": "Writing Manim code…",
    "CodeAgentNode": "Writing Manim code…",
    "starting": "Starting animation pipeline…",
    "compile": "Compiling Manim scene…",
    "render": "Rendering video…",
    "assemble": "Assembling final video…",
    "upload": "Uploading video…",
}


def _resolve_scene_file_for_upload(
    artifact: dict[str, Any],
    run_dir: str | None,
) -> Path | None:
    """Locate Manim/Python source for S3 upload from artifact or run_dir."""
    hint = artifact.get("scene_file")
    if hint:
        hint_path = Path(hint)
        if hint_path.is_file():
            return hint_path
        if run_dir:
            nested = Path(run_dir) / hint
            if nested.is_file():
                return nested

    if not run_dir:
        return None
    root = Path(run_dir)
    if not root.is_dir():
        return None

    mode = artifact.get("mode")
    if mode == "lecture":
        lecture_py = root / "lecture.py"
        if lecture_py.is_file():
            return lecture_py

    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        scene_rel = manifest.get("scene_file")
        if scene_rel:
            scene_path = (
                Path(scene_rel) if Path(scene_rel).is_absolute() else root / scene_rel
            )
            if scene_path.is_file():
                return scene_path

    return None


def _friendly_stage_message(stage: str) -> str:
    if stage in _STAGE_MESSAGES:
        return _STAGE_MESSAGES[stage]
    # CamelCase / snake → readable fallback
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", stage).replace("_", " ")
    return f"{spaced}…"


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


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


def _notify_video_status_sync(payload: dict[str, Any]) -> None:
    """Publish from the sync CLI-reader thread (no event loop)."""
    try:
        r = redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )
        try:
            r.publish(VIDEO_STATUS_CHANNEL, json.dumps(payload, default=str))
        finally:
            r.close()
    except Exception as exc:
        logger.warning("Failed to publish video_status (sync): %s", exc)


def _parse_progress_stage(line: str) -> str | None:
    cleaned = _strip_ansi(line).strip()
    match = _NODE_PROGRESS_RE.search(cleaned)
    if not match:
        return None
    return match.group(1)


def _run_agents_cli(
    mode: str,
    prompt: str,
    *,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    model_name: str | None = None,
    generation_id: str | None = None,
    conversation_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Invoke ``cli.py animate|generate --json`` and parse the VideoArtifact.

    Streams ``-> {node}`` progress lines to Redis while the process runs.
    """
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
    # Force unbuffered / line-buffered Python so progress appears promptly.
    env["PYTHONUNBUFFERED"] = "1"
    # Host Celery often inherits backend VIRTUAL_ENV; agents `uv run` must use apps/agents.
    env.pop("VIRTUAL_ENV", None)
    custom_base = (llm_base_url or "").strip()
    custom_key = (llm_api_key or "").strip()
    custom_model = (model_name or "").strip()

    if custom_base:
        # BYOK / local OpenAI-compatible endpoint for all pipeline roles.
        env["AOS_OPENAI_BASE_URL"] = custom_base
        env["AOS_OPENAI_API_KEY"] = custom_key or "local"
        if custom_model:
            env["AOS_OPENAI_MODEL"] = custom_model
            # Keep role overrides aligned so lecture hardcodes via llm_config pick it up.
            for role_env in (
                "AOS_CLASSIFIER_MODEL",
                "AOS_PLANNER_MODEL",
                "AOS_CODER_MODEL",
                "AOS_ANIMATION_MODEL",
                "AOS_OPENROUTER_MODEL",
            ):
                env[role_env] = custom_model
        env["AOS_MODEL_PROFILE"] = "openai_compatible"
    else:
        # UI Animate path: force OpenRouter for the full Classify→Plan→Code graph
        # (default agents profile is hybrid and expects Ollama for the coder).
        env["AOS_MODEL_PROFILE"] = "cloud"
        openrouter_key = custom_key or settings.OPENROUTER_API_KEY
        if openrouter_key:
            env["OPENROUTER_API_KEY"] = openrouter_key
        if custom_model:
            env["AOS_OPENROUTER_MODEL"] = (
                custom_model
                if custom_model.startswith("openrouter:")
                else f"openrouter:{custom_model}"
            )
            for role_env in (
                "AOS_CLASSIFIER_MODEL",
                "AOS_PLANNER_MODEL",
                "AOS_CODER_MODEL",
                "AOS_ANIMATION_MODEL",
            ):
                env[role_env] = env["AOS_OPENROUTER_MODEL"]

    def publish_stage(stage: str, message: str | None = None) -> None:
        if not generation_id:
            return
        _notify_video_status_sync(
            {
                "type": "video_status",
                "video_generation_id": generation_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "status": "running",
                "stage": stage,
                "message": message or _friendly_stage_message(stage),
                "mode": mode,
                "prompt": prompt,
            }
        )

    proc = subprocess.Popen(
        cmd,
        cwd=str(agents_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
    )

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    seen_stages: set[str] = set()

    def _read_stream(
        stream: Any,
        sink: list[str],
        *,
        on_line: Callable[[str], None] | None = None,
    ) -> None:
        assert stream is not None
        for line in stream:
            sink.append(line)
            if on_line is not None:
                on_line(line)

    def _on_progress_line(line: str) -> None:
        stage = _parse_progress_stage(line)
        if not stage or stage in seen_stages:
            return
        seen_stages.add(stage)
        publish_stage(stage)

    stdout_thread = threading.Thread(
        target=_read_stream,
        args=(proc.stdout, stdout_chunks),
        kwargs={"on_line": _on_progress_line},
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_stream,
        args=(proc.stderr, stderr_chunks),
        kwargs={"on_line": _on_progress_line},
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    returncode = proc.wait()
    stdout_thread.join(timeout=30)
    stderr_thread.join(timeout=30)

    stdout = "".join(stdout_chunks).strip()
    stderr = "".join(stderr_chunks).strip()
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
                f"agents CLI returned no JSON (exit={returncode}): "
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
    prompt: str,
    ok: bool,
    minio_key: str | None,
    error: str | None,
    existing_assistant_message_id: UUID | None = None,
) -> UUID | None:
    """Persist or update assistant message + generate_video tool call; return message id."""
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
                "prompt": prompt,
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
                "prompt": prompt,
                "status": "failed",
                "error": error,
            }
        )
        success = False

    external_tc_id = f"generate_video_{generation_id}"

    async with get_worker_db_context() as db:
        conv = ConversationService(db)

        if existing_assistant_message_id is not None:
            try:
                await conv.update_message_content(existing_assistant_message_id, content)
                tc = await conv.get_tool_call_by_external_id(external_tc_id)
                if tc is not None:
                    await conv.complete_tool_call(
                        tc.id,
                        ToolCallComplete(
                            result=tool_result,
                            completed_at=datetime.now(UTC),
                            success=success,
                        ),
                    )
                    return existing_assistant_message_id
            except Exception:
                logger.exception(
                    "Failed to update existing assistant message %s; creating new one",
                    existing_assistant_message_id,
                )

        msg = await conv.add_message(
            conversation_id,
            MessageCreate(role="assistant", content=content, model_name="manim-pipeline"),
        )
        tc = await conv.start_tool_call(
            msg.id,
            ToolCallCreate(
                tool_call_id=external_tc_id,
                tool_name="generate_video",
                args={
                    "mode": mode,
                    "video_generation_id": str(generation_id),
                    "prompt": prompt,
                },
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


async def _run_generate_video(
    generation_id: str,
    *,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
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
        existing_assistant_message_id = row.assistant_message_id
        object_key = svc.build_object_key(row)
        code_key = svc.build_code_object_key(row)

    await _notify_video_status(
        {
            "type": "video_status",
            "video_generation_id": generation_id,
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
            "status": "running",
            "stage": "starting",
            "message": "Starting animation pipeline…",
            "mode": mode,
            "prompt": prompt,
        }
    )

    artifact = await asyncio.to_thread(
        _run_agents_cli,
        mode,
        prompt,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        model_name=model_name,
        generation_id=generation_id,
        conversation_id=str(conversation_id),
        user_id=str(user_id),
    )
    run_dir = artifact.get("run_dir")

    if not artifact.get("ok") or not artifact.get("video_path"):
        error = (
            artifact.get("error")
            or artifact.get("stopped_reason")
            or "video_pipeline_failed"
        )
        if error == "completed" and not artifact.get("video_path"):
            summary = (artifact.get("summary") or artifact.get("message") or "").strip()
            error = (
                f"pipeline_finished_without_video: {summary[:400]}"
                if summary
                else "pipeline_finished_without_video"
            )
        assistant_id = await _persist_assistant_result(
            conversation_id=conversation_id,
            generation_id=gid,
            mode=mode,
            prompt=prompt,
            ok=False,
            minio_key=None,
            error=error,
            existing_assistant_message_id=existing_assistant_message_id,
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
                "stage": "failed",
                "message": f"Video generation failed: {error}",
                "mode": mode,
                "prompt": prompt,
                "error": error,
            }
        )
        return {"status": "failed", "error": error}

    video_path = artifact["video_path"]
    code_minio_key: str | None = None
    try:
        await _notify_video_status(
            {
                "type": "video_status",
                "video_generation_id": generation_id,
                "conversation_id": str(conversation_id),
                "user_id": str(user_id),
                "status": "running",
                "stage": "upload",
                "message": "Uploading video…",
                "mode": mode,
                "prompt": prompt,
            }
        )
        storage = get_video_storage()
        storage.upload_file(video_path, object_key, content_type="video/mp4")
        scene_path = _resolve_scene_file_for_upload(artifact, run_dir)
        if scene_path is not None:
            try:
                storage.upload_file(
                    scene_path,
                    code_key,
                    content_type="text/x-python",
                )
                code_minio_key = code_key
            except Exception:
                logger.exception(
                    "Scene source upload failed for %s (video upload succeeded)",
                    generation_id,
                )
        else:
            logger.warning(
                "No scene_file found for generation %s; skipping code upload",
                generation_id,
            )
    except Exception as exc:
        error = f"minio_upload_failed: {exc}"
        logger.exception("MinIO upload failed for %s", generation_id)
        assistant_id = await _persist_assistant_result(
            conversation_id=conversation_id,
            generation_id=gid,
            mode=mode,
            prompt=prompt,
            ok=False,
            minio_key=None,
            error=error,
            existing_assistant_message_id=existing_assistant_message_id,
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
                "stage": "upload",
                "message": f"Upload failed: {error}",
                "mode": mode,
                "prompt": prompt,
                "error": error,
            }
        )
        return {"status": "failed", "error": error}

    assistant_id = await _persist_assistant_result(
        conversation_id=conversation_id,
        generation_id=gid,
        mode=mode,
        prompt=prompt,
        ok=True,
        minio_key=object_key,
        error=None,
        existing_assistant_message_id=existing_assistant_message_id,
    )
    async with get_worker_db_context() as db:
        await VideoGenerationService(db).mark_completed(
            gid,
            minio_key=object_key,
            run_dir=run_dir,
            assistant_message_id=assistant_id,
            code_minio_key=code_minio_key,
        )

    await _notify_video_status(
        {
            "type": "video_status",
            "video_generation_id": generation_id,
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
            "status": "completed",
            "stage": "completed",
            "message": "Your video is ready.",
            "mode": mode,
            "prompt": prompt,
            "minio_key": object_key,
            "code_minio_key": code_minio_key,
            "assistant_message_id": str(assistant_id) if assistant_id else None,
        }
    )
    return {
        "status": "completed",
        "minio_key": object_key,
        "code_minio_key": code_minio_key,
    }


@shared_task(
    bind=True,
    max_retries=0,
    soft_time_limit=_SOFT_LIMIT,
    time_limit=_HARD_LIMIT,
)  # type: ignore[misc]
def generate_video_task(
    self: Any,
    generation_id: str,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Run Manim pipeline via agents CLI, upload MP4 to MinIO, update DB."""
    logger.info("generate_video_task start: %s", generation_id)
    try:
        return asyncio.run(
            _run_generate_video(
                generation_id,
                llm_base_url=llm_base_url,
                llm_api_key=llm_api_key,
                model_name=model_name,
            )
        )
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

"""Video generation service — enqueue Manim jobs and query MinIO-backed results."""

from __future__ import annotations

import logging
from typing import BinaryIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.video_generation import VideoGeneration
from app.repositories import video_generation as video_repo
from app.schemas.video_generation import VideoGenerationCreate, VideoGenerationList, VideoGenerationRead
from app.services.video_storage import get_video_storage, video_object_key

logger = logging.getLogger(__name__)

VALID_MODES = frozenset({"animate", "lecture"})


class VideoGenerationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_pending(
        self,
        *,
        user_id: UUID,
        data: VideoGenerationCreate,
    ) -> VideoGeneration:
        if data.mode not in VALID_MODES:
            raise BadRequestError(
                message="Invalid video mode",
                details={"mode": data.mode, "allowed": sorted(VALID_MODES)},
            )
        return await video_repo.create(
            self.db,
            user_id=user_id,
            conversation_id=data.conversation_id,
            prompt=data.prompt,
            mode=data.mode,
            user_message_id=data.user_message_id,
            status="pending",
        )

    async def get_for_user(self, generation_id: UUID, user_id: UUID) -> VideoGeneration:
        row = await video_repo.get_by_id(self.db, generation_id)
        if row is None or row.user_id != user_id:
            raise NotFoundError(
                message="Video generation not found",
                details={"id": str(generation_id)},
            )
        return row

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        conversation_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> VideoGenerationList:
        rows, total = await video_repo.list_for_user(
            self.db,
            user_id=user_id,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
        )
        return VideoGenerationList(
            items=[VideoGenerationRead.model_validate(r) for r in rows],
            total=total,
        )

    async def set_celery_task(self, generation_id: UUID, task_id: str) -> VideoGeneration:
        row = await video_repo.get_by_id(self.db, generation_id)
        if row is None:
            raise NotFoundError(message="Video generation not found", details={"id": str(generation_id)})
        return await video_repo.update(self.db, row, celery_task_id=task_id)

    async def set_assistant_message(
        self, generation_id: UUID, assistant_message_id: UUID
    ) -> VideoGeneration:
        row = await video_repo.get_by_id(self.db, generation_id)
        if row is None:
            raise NotFoundError(message="Video generation not found", details={"id": str(generation_id)})
        return await video_repo.update(
            self.db, row, assistant_message_id=assistant_message_id
        )

    async def get_by_id(self, generation_id: UUID) -> VideoGeneration | None:
        return await video_repo.get_by_id(self.db, generation_id)

    async def mark_running(self, generation_id: UUID) -> VideoGeneration:
        row = await video_repo.get_by_id(self.db, generation_id)
        if row is None:
            raise NotFoundError(message="Video generation not found", details={"id": str(generation_id)})
        return await video_repo.update(self.db, row, status="running", error_message=None)

    async def mark_completed(
        self,
        generation_id: UUID,
        *,
        minio_key: str,
        minio_bucket: str | None = None,
        run_dir: str | None = None,
        assistant_message_id: UUID | None = None,
    ) -> VideoGeneration:
        row = await video_repo.get_by_id(self.db, generation_id)
        if row is None:
            raise NotFoundError(message="Video generation not found", details={"id": str(generation_id)})
        return await video_repo.update(
            self.db,
            row,
            status="completed",
            minio_key=minio_key,
            minio_bucket=minio_bucket or settings.S3_VIDEO_BUCKET,
            run_dir=run_dir,
            assistant_message_id=assistant_message_id,
            error_message=None,
        )

    async def mark_failed(
        self,
        generation_id: UUID,
        *,
        error_message: str,
        run_dir: str | None = None,
        assistant_message_id: UUID | None = None,
    ) -> VideoGeneration:
        row = await video_repo.get_by_id(self.db, generation_id)
        if row is None:
            raise NotFoundError(message="Video generation not found", details={"id": str(generation_id)})
        return await video_repo.update(
            self.db,
            row,
            status="failed",
            error_message=error_message[:4000],
            run_dir=run_dir,
            assistant_message_id=assistant_message_id,
        )

    def build_object_key(self, row: VideoGeneration) -> str:
        return video_object_key(
            user_id=row.user_id,
            conversation_id=row.conversation_id,
            generation_id=row.id,
        )

    def open_stream_for(self, row: VideoGeneration) -> BinaryIO:
        if not row.minio_key or row.status != "completed":
            raise NotFoundError(
                message="Video not ready",
                details={"id": str(row.id), "status": row.status},
            )
        storage = get_video_storage()
        return storage.open_stream(row.minio_key)

    def enqueue(
        self,
        generation_id: UUID,
        *,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        model_name: str | None = None,
    ) -> str:
        """Enqueue Celery task; returns task id.

        LLM credentials are passed as Celery kwargs only (not persisted to DB).
        """
        from app.worker.tasks.video_tasks import generate_video_task

        async_result = generate_video_task.delay(
            str(generation_id),
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            model_name=model_name,
        )
        return str(async_result.id)

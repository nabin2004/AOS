"""Schemas for video generation jobs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema

VideoMode = Literal["animate", "lecture"]
VideoStatus = Literal["pending", "running", "completed", "failed"]


class VideoGenerationRead(BaseSchema):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    user_message_id: UUID | None = None
    assistant_message_id: UUID | None = None
    prompt: str
    mode: str
    status: str
    minio_bucket: str | None = None
    minio_key: str | None = None
    code_minio_key: str | None = None
    error_message: str | None = None
    run_dir: str | None = None
    celery_task_id: str | None = None
    progress_stage: str | None = None
    progress_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class VideoGenerationList(BaseSchema):
    items: list[VideoGenerationRead]
    total: int


class VideoGenerationCreate(BaseSchema):
    prompt: str = Field(min_length=1)
    mode: VideoMode
    conversation_id: UUID
    user_message_id: UUID | None = None

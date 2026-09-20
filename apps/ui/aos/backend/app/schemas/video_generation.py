"""Schemas for video generation jobs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema

VideoMode = Literal["animate", "keyframe", "lecture", "teaching"]
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


class VideoClassifyRequest(BaseSchema):
    text: str = Field(min_length=1)


class VideoClassifyResponse(BaseSchema):
    animatable: bool
    subject: str = "unknown"
    topic: str = ""
    reason: str = ""


class VideoPlanRequest(BaseSchema):
    text: str = Field(min_length=1)
    hints: str | None = None
    model_name: str | None = None
    base_url: str | None = None
    api_key: str | None = None


class VideoPlanResponse(BaseSchema):
    plan: str
    title: str = "Educational Animation Plan"
    topic: str = ""


class VideoCodeRequest(BaseSchema):
    plan: str = Field(min_length=1)
    knowledge_text: str | None = None
    scene_name: str | None = None
    model_name: str | None = None
    base_url: str | None = None
    api_key: str | None = None


class VideoCodeResponse(BaseSchema):
    code: str
    scene_name: str = "GeneratedScene"


class VideoRenderCustomRequest(BaseSchema):
    code: str = Field(min_length=1)
    scene_name: str | None = None
    quality: Literal["l", "m", "h", "k"] = "l"
    conversation_id: UUID | None = None
    prompt: str | None = None


class VideoRenderCustomResponse(BaseSchema):
    video_generation_id: UUID
    status: str
    stream_url: str
    scene_name: str
    quality: str
    code: str | None = None

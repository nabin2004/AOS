"""MinIO / S3 storage for compiled Manim videos."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def video_object_key(
    *,
    user_id: UUID | str,
    conversation_id: UUID | str,
    generation_id: UUID | str,
) -> str:
    """Canonical object key for a generation MP4."""
    return f"videos/{user_id}/{conversation_id}/{generation_id}.mp4"


class VideoStorage:
    """Upload / stream compiled videos from the configured S3-compatible bucket."""

    def __init__(self) -> None:
        self.bucket = settings.S3_VIDEO_BUCKET
        self._client: BaseClient | None = None
        self._bucket_ready = False

    def _get_client(self) -> BaseClient:
        if self._client is not None:
            return self._client
        if not settings.S3_VIDEO_ENDPOINT:
            raise RuntimeError(
                "S3_VIDEO_ENDPOINT is not set. Point it at MinIO "
                "(e.g. http://localhost:9010 for local compose)."
            )
        kwargs: dict[str, Any] = {
            "aws_access_key_id": settings.S3_VIDEO_ACCESS_KEY or None,
            "aws_secret_access_key": settings.S3_VIDEO_SECRET_KEY or None,
            "region_name": settings.S3_VIDEO_REGION,
            "endpoint_url": settings.S3_VIDEO_ENDPOINT,
            "config": Config(signature_version="s3v4"),
        }
        self._client = boto3.client("s3", **kwargs)
        return self._client

    def ensure_bucket(self) -> None:
        """Create the video bucket if it does not exist."""
        if self._bucket_ready:
            return
        client = self._get_client()
        try:
            client.head_bucket(Bucket=self.bucket)
        except ClientError:
            logger.info("Creating video bucket %s", self.bucket)
            create_kwargs: dict[str, Any] = {"Bucket": self.bucket}
            # MinIO / us-east-1 often omit LocationConstraint
            if settings.S3_VIDEO_REGION and settings.S3_VIDEO_REGION != "us-east-1":
                create_kwargs["CreateBucketConfiguration"] = {
                    "LocationConstraint": settings.S3_VIDEO_REGION
                }
            client.create_bucket(**create_kwargs)
        self._bucket_ready = True

    def upload_file(self, local_path: str | Path, key: str) -> str:
        """Upload a local MP4 and return the object key."""
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"Video file not found: {path}")
        self.ensure_bucket()
        client = self._get_client()
        client.upload_file(
            str(path),
            self.bucket,
            key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        logger.info("Uploaded video to s3://%s/%s", self.bucket, key)
        return key

    def open_stream(self, key: str) -> BinaryIO:
        """Return a streaming body for the object (caller must close)."""
        self.ensure_bucket()
        client = self._get_client()
        response = client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"]

    def object_exists(self, key: str) -> bool:
        try:
            self.ensure_bucket()
            self._get_client().head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False


def get_video_storage() -> VideoStorage:
    return VideoStorage()

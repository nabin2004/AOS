"""MinIO / S3 storage utilities for AOS Agents."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

def get_minio_client() -> Any:
    """Build a boto3 S3 client using the agents' environment configuration."""
    endpoint = os.getenv("S3_VIDEO_ENDPOINT", "http://localhost:9010")
    access_key = os.getenv("S3_VIDEO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("S3_VIDEO_SECRET_KEY", "minioadmin")
    region = os.getenv("S3_VIDEO_REGION", "us-east-1")

    config = Config(signature_version="s3v4")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=config,
    )
    return client

def ensure_bucket(client: Any, bucket_name: str, region: str = "us-east-1") -> None:
    """Check if target bucket exists, and create it if missing."""
    try:
        client.head_bucket(Bucket=bucket_name)
    except ClientError:
        logger.info("Creating MinIO bucket %s", bucket_name)
        create_kwargs: dict[str, Any] = {"Bucket": bucket_name}
        if region and region != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {
                "LocationConstraint": region
            }
        client.create_bucket(**create_kwargs)

def upload_to_minio(
    local_path: str | Path,
    object_key: str | None = None,
    content_type: str = "video/mp4",
) -> str:
    """Uploads a local file to the configured MinIO bucket and returns its access URL."""
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for MinIO upload: {path}")

    bucket = os.getenv("S3_VIDEO_BUCKET", "aos-videos")
    region = os.getenv("S3_VIDEO_REGION", "us-east-1")

    if object_key is None:
        # Generate default unique key using file name and UUID
        object_key = f"videos/{uuid.uuid4()}/{path.name}"

    client = get_minio_client()
    ensure_bucket(client, bucket, region)

    logger.info("Uploading %s to s3://%s/%s ...", path, bucket, object_key)
    client.upload_file(
        str(path),
        bucket,
        object_key,
        ExtraArgs={"ContentType": content_type},
    )

    # Return access URL
    endpoint = os.getenv("S3_VIDEO_ENDPOINT", "http://localhost:9010")
    try:
        # Generate presigned URL valid for 7 days
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=3600 * 24 * 7,
        )
        return url
    except Exception as e:
        logger.warning("Could not generate presigned URL, returning direct URL fallback: %s", e)
        return f"{endpoint.rstrip('/')}/{bucket}/{object_key}"

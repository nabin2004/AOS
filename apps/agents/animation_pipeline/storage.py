"""Artifact and storage management for the animation pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any
import uuid

from coder_run import CoderRunResult


class PipelineArtifactManager:
    """Encapsulates artifact discovery and remote object storage uploads."""

    def __init__(self, s3_endpoint: str | None = None) -> None:
        self.s3_endpoint = s3_endpoint or os.getenv("S3_VIDEO_ENDPOINT")

    def find_compiled_video(self, run_dir: str | None) -> Path | None:
        """Locate the compiled MP4 in the run directory, inspecting manifest.json first."""
        if not run_dir:
            return None
        root = Path(run_dir)
        if not root.is_dir():
            return None

        manifest_path = root / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                last = manifest.get("last_compile") or {}
                candidate = last.get("video_path") or manifest.get("video_path")
                if candidate and Path(candidate).is_file():
                    return Path(candidate)
            except Exception:
                pass

        for path in root.rglob("*.mp4"):
            if path.is_file() and "partial_movie_files" not in path.parts:
                return path
        return None

    def upload_artifacts(
        self, coder_result: CoderRunResult, result_dict: dict[str, Any]
    ) -> None:
        """Upload video and Python scene files to MinIO/S3 if an endpoint is configured."""
        if not self.s3_endpoint:
            return

        try:
            from tools.minio_storage import upload_to_minio

            video_path = self.find_compiled_video(coder_result.run_dir)
            if video_path and video_path.is_file():
                gen_id = uuid.uuid4()
                video_key = f"videos/pipeline/{gen_id}.mp4"
                code_key = f"videos/pipeline/{gen_id}.py"

                video_url = upload_to_minio(
                    video_path, object_key=video_key, content_type="video/mp4"
                )
                result_dict["minio_url"] = video_url
                result_dict["minio_key"] = video_key
                print(f"[minio] Uploaded video to {video_url}", file=sys.stderr, flush=True)

                if coder_result.scene_file:
                    scene_path = Path(coder_result.run_dir) / coder_result.scene_file
                    if scene_path.is_file():
                        code_url = upload_to_minio(
                            scene_path,
                            object_key=code_key,
                            content_type="text/x-python",
                        )
                        result_dict["code_minio_url"] = code_url
                        result_dict["code_minio_key"] = code_key
                        print(
                            f"[minio] Uploaded scene code to {code_url}",
                            file=sys.stderr,
                            flush=True,
                        )
        except Exception as exc:
            print(f"[minio] Upload failed: {exc}", file=sys.stderr, flush=True)

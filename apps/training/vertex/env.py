"""Vertex AI environment helpers for AOS training jobs."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")


def vertex_model_dir() -> Path | None:
    raw = os.environ.get("AIP_MODEL_DIR", "").strip()
    return Path(raw) if raw else None


def vertex_tensorboard_dir() -> Path | None:
    raw = os.environ.get("AIP_TENSORBOARD_LOG_DIR", "").strip()
    return Path(raw) if raw else None


def on_vertex() -> bool:
    return vertex_model_dir() is not None or bool(os.environ.get("CLOUD_ML_JOB_ID"))


def apply_vertex_output_dir(config: T, *, output_field: str = "output_dir") -> T:
    """Point training output at Vertex AIP_MODEL_DIR when set."""
    from dataclasses import replace

    model_dir = vertex_model_dir()
    if model_dir is None:
        return config
    return replace(config, **{output_field: model_dir})


def apply_vertex_sft_reporting(config: T) -> T:
    """Use TensorBoard on Vertex when AIP_TENSORBOARD_LOG_DIR is set."""
    from dataclasses import replace

    if vertex_tensorboard_dir() is None:
        return config
    if getattr(config, "report_to", "none") == "none":
        return config
    if getattr(config, "report_to", "") == "wandb":
        return replace(config, report_to="tensorboard")
    return config


def sft_tensorboard_logging_dir() -> str | None:
    tb_dir = vertex_tensorboard_dir()
    return str(tb_dir) if tb_dir else None


def download_gcs_file(gcs_uri: str, dest: Path) -> None:
    """Download a single GCS object to a local path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return

    try:
        from google.cloud import storage
    except ImportError:
        _run_gsutil(["cp", gcs_uri, str(dest)])
        return

    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got: {gcs_uri}")

    bucket_name, _, blob_name = gcs_uri.removeprefix("gs://").partition("/")
    if not blob_name:
        raise ValueError(f"GCS URI must include an object path: {gcs_uri}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    bucket.blob(blob_name).download_to_filename(str(dest))
    print(f"Downloaded {gcs_uri} -> {dest}", flush=True)


def download_gcs_prefix(gcs_uri: str, dest_dir: Path) -> None:
    """Download all objects under a GCS prefix into dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got: {gcs_uri}")

    prefix_uri = gcs_uri.rstrip("/") + "/"

    try:
        from google.cloud import storage
    except ImportError:
        _run_gsutil(["-m", "cp", "-r", prefix_uri, str(dest_dir)])
        return

    bucket_name, _, prefix = prefix_uri.removeprefix("gs://").partition("/")
    client = storage.Client()
    blobs = client.list_blobs(bucket_name, prefix=prefix)
    downloaded = 0
    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        rel = blob.name[len(prefix) :] if blob.name.startswith(prefix) else blob.name
        target = dest_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(target))
        downloaded += 1

    if downloaded == 0:
        raise FileNotFoundError(f"No objects found at {prefix_uri}")
    print(
        f"Downloaded {downloaded} object(s) from {prefix_uri} -> {dest_dir}", flush=True
    )


def _run_gsutil(args: list[str]) -> None:
    cmd = ["gsutil", *args]
    print(f"Running: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def load_env_file(path: Path) -> dict[str, str]:
    """Load KEY=VALUE lines from a dotenv-style file (no export prefix)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def require_env(name: str, values: dict[str, str] | None = None) -> str:
    raw = os.environ.get(name) or (values or {}).get(name, "")
    raw = raw.strip()
    if not raw:
        print(f"ERROR: missing required setting {name}", file=sys.stderr)
        raise SystemExit(1)
    return raw

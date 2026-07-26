"""Shared helpers for Vertex AI CustomJob submission."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from google.cloud import aiplatform

VERTEX_ROOT = Path(__file__).resolve().parent


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", default=None, help="GCP project id")
    parser.add_argument("--region", default=None, help="Vertex AI region")
    parser.add_argument("--bucket", default=None, help="GCS bucket name (no gs://)")
    parser.add_argument("--repo", default=None, help="Artifact Registry repo name")
    parser.add_argument(
        "--image", default=None, help="Full container image URI override"
    )
    parser.add_argument("--machine-type", default=None)
    parser.add_argument("--accelerator-type", default=None)
    parser.add_argument("--accelerator-count", type=int, default=None)
    parser.add_argument("--boot-disk-gb", type=int, default=None)
    parser.add_argument(
        "--env-file",
        default=str(VERTEX_ROOT / "config.env"),
        help="Optional KEY=VALUE file (default: config.env if present)",
    )
    parser.add_argument("--sync", action="store_true", help="Wait for job completion")
    parser.add_argument("--display-name", default=None)


def load_settings(args: argparse.Namespace) -> dict[str, str]:
    from env import load_env_file

    file_values: dict[str, str] = {}
    env_path = Path(args.env_file)
    if env_path.is_file():
        file_values = load_env_file(env_path)

    def pick(name: str, arg_value: object | None, default: str = "") -> str:
        if arg_value is not None and str(arg_value).strip():
            return str(arg_value).strip()
        env_value = os.environ.get(name, "").strip()
        if env_value:
            return env_value
        return file_values.get(name, default).strip()

    settings = {
        "GCP_PROJECT": pick("GCP_PROJECT", args.project),
        "GCP_REGION": pick("GCP_REGION", args.region, "us-central1"),
        "GCS_BUCKET": pick("GCS_BUCKET", args.bucket),
        "ARTIFACT_REPO": pick("ARTIFACT_REPO", args.repo, "aos-training"),
        "MACHINE_TYPE": pick("MACHINE_TYPE", args.machine_type, "a2-ultragpu-1g"),
        "ACCELERATOR_TYPE": pick(
            "ACCELERATOR_TYPE", args.accelerator_type, "NVIDIA_TESLA_A100"
        ),
        "ACCELERATOR_COUNT": pick("ACCELERATOR_COUNT", args.accelerator_count, "1"),
        "BOOT_DISK_GB": pick("BOOT_DISK_GB", args.boot_disk_gb, "500"),
    }
    return settings


def require_settings(settings: dict[str, str], *keys: str) -> None:
    missing = [key for key in keys if not settings.get(key)]
    if missing:
        raise SystemExit(f"Missing required settings: {', '.join(missing)}")


def default_image_uri(settings: dict[str, str], tag: str) -> str:
    region = settings["GCP_REGION"]
    project = settings["GCP_PROJECT"]
    repo = settings["ARTIFACT_REPO"]
    return f"{region}-docker.pkg.dev/{project}/{repo}/{tag}:latest"


def collect_wandb_env_vars(
    *,
    project: str,
    run_name: str | None = None,
    project_env_key: str | None = None,
    group: str | None = None,
    tags: tuple[str, ...] | list[str] | None = None,
) -> dict[str, str]:
    training_root = VERTEX_ROOT.parent
    if str(training_root) not in sys.path:
        sys.path.insert(0, str(training_root))
    from wandb_env import collect_wandb_env_vars as _collect_wandb_env_vars

    return _collect_wandb_env_vars(
        project=project,
        run_name=run_name,
        project_env_key=project_env_key,
        group=group,
        tags=tags,
    )


def merge_training_env_vars(
    *,
    wandb_project: str,
    wandb_run_name: str | None = None,
    wandb_project_env_key: str | None = None,
    wandb_group: str | None = None,
    wandb_tags: tuple[str, ...] | list[str] | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    env_vars = dict(extra or {})
    env_vars.update(
        collect_wandb_env_vars(
            project=wandb_project,
            run_name=wandb_run_name,
            project_env_key=wandb_project_env_key,
            group=wandb_group,
            tags=wandb_tags,
        )
    )
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token:
        env_vars["HF_TOKEN"] = hf_token
    return env_vars


def build_worker_pool(
    settings: dict[str, str],
    *,
    image_uri: str,
    args: list[str],
    env_vars: dict[str, str] | None = None,
) -> list[dict]:
    machine_spec: dict[str, object] = {
        "machine_type": settings["MACHINE_TYPE"],
    }
    accel_type = settings.get("ACCELERATOR_TYPE", "").strip()
    accel_count = int(settings.get("ACCELERATOR_COUNT", "0") or "0")
    if accel_type and accel_count > 0:
        machine_spec["accelerator_type"] = accel_type
        machine_spec["accelerator_count"] = accel_count

    boot_disk = int(settings.get("BOOT_DISK_GB", "500") or "500")
    container_env = [
        {"name": key, "value": value} for key, value in (env_vars or {}).items()
    ]

    return [
        {
            "machine_spec": machine_spec,
            "replica_count": 1,
            "disk_spec": {
                "boot_disk_type": "pd-ssd",
                "boot_disk_size_gb": boot_disk,
            },
            "container_spec": {
                "image_uri": image_uri,
                "command": ["/entrypoint.sh"],
                "args": args,
                "env": container_env,
            },
        }
    ]


def submit_custom_job(
    *,
    settings: dict[str, str],
    display_name: str,
    image_uri: str,
    base_output_dir: str,
    container_args: list[str],
    env_vars: dict[str, str] | None = None,
    sync: bool = False,
) -> aiplatform.CustomJob:
    project = settings["GCP_PROJECT"]
    region = settings["GCP_REGION"]
    bucket = settings["GCS_BUCKET"]
    staging_bucket = f"gs://{bucket}/staging"

    aiplatform.init(project=project, location=region, staging_bucket=staging_bucket)

    job = aiplatform.CustomJob(
        display_name=display_name,
        worker_pool_specs=build_worker_pool(
            settings,
            image_uri=image_uri,
            args=container_args,
            env_vars=env_vars,
        ),
        base_output_dir=base_output_dir,
    )
    job.run(sync=sync)
    print(f"Submitted Vertex job: {display_name}")
    print(f"  image: {image_uri}")
    print(f"  output: {base_output_dir}")
    return job

#!/usr/bin/env python3
"""Submit Phase 1 SFT training to Vertex AI Custom Jobs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from job_common import (
    add_common_args,
    default_image_uri,
    load_settings,
    merge_training_env_vars,
    require_settings,
    submit_custom_job,
)

TRAINING_ROOT = Path(__file__).resolve().parents[1]
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from model_identity import (  # noqa: E402
    VERTEX_SFT_DISPLAY_NAME,
    WANDB_RUN_GROUP,
    WANDB_SFT_RUN_NAME,
    WANDB_TAGS,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Submit AOS SFT job to Vertex AI")
    add_common_args(parser)
    parser.add_argument(
        "--data-uri",
        required=True,
        help="GCS URI to trajectories.jsonl (gs://bucket/data/trajectories.jsonl)",
    )
    parser.add_argument(
        "--output-prefix",
        default="artifacts/sft",
        help="Bucket-relative output prefix (default: artifacts/sft)",
    )
    parser.add_argument(
        "--report-to",
        default=None,
        help="Logging backend (default: wandb if WANDB_API_KEY set, else tensorboard)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a minimal SFT job (1 epoch, batch size 1)",
    )
    parser.set_defaults(display_name=VERTEX_SFT_DISPLAY_NAME)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    settings = load_settings(args)
    require_settings(settings, "GCP_PROJECT", "GCS_BUCKET")

    image_uri = args.image or default_image_uri(settings, "sft")
    bucket = settings["GCS_BUCKET"]
    base_output_dir = f"gs://{bucket}/{args.output_prefix.strip('/')}"

    env_vars = merge_training_env_vars(
        wandb_project="aos-sft",
        wandb_run_name=WANDB_SFT_RUN_NAME,
        wandb_project_env_key="WANDB_PROJECT_SFT",
        wandb_group=WANDB_RUN_GROUP,
        wandb_tags=[*WANDB_TAGS, "sft"],
    )

    report_to = args.report_to
    if report_to is None:
        report_to = "wandb" if env_vars.get("WANDB_API_KEY") else "tensorboard"

    container_args = [
        "--data-uri",
        args.data_uri,
        "--report-to",
        report_to,
    ]
    if args.smoke:
        container_args.append("--smoke")

    submit_custom_job(
        settings=settings,
        display_name=args.display_name,
        image_uri=image_uri,
        base_output_dir=base_output_dir,
        container_args=container_args,
        env_vars=env_vars,
        sync=args.sync,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

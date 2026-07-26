#!/usr/bin/env python3
"""Submit Phase 2 GRPO training to Vertex AI Custom Jobs."""

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

from model_identity import WANDB_GRPO_RUN_NAME, WANDB_RUN_GROUP, WANDB_TAGS  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Submit AOS GRPO job to Vertex AI")
    add_common_args(parser)
    parser.add_argument(
        "--sft-lora-uri",
        default=None,
        help="GCS prefix for Phase 1 SFT adapter (gs://bucket/artifacts/sft/.../)",
    )
    parser.add_argument(
        "--dataset-uri",
        default=None,
        help="Optional GCS URI for ManiBench_Pilot_Dataset.json",
    )
    parser.add_argument(
        "--output-prefix",
        default="artifacts/grpo",
        help="Bucket-relative output prefix (default: artifacts/grpo)",
    )
    parser.add_argument(
        "--report-to",
        default=None,
        help="Logging backend (default: wandb if WANDB_API_KEY set, else none)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one GRPO step for a GPU smoke test",
    )
    parser.add_argument(
        "--grpo-only",
        action="store_true",
        help="Skip frozen SFT adapter (train GRPO LoRA on base only)",
    )
    parser.set_defaults(display_name="aos-grpo-gemma4-31b-manim")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    settings = load_settings(args)
    require_settings(settings, "GCP_PROJECT", "GCS_BUCKET")

    if not args.grpo_only and not args.sft_lora_uri:
        raise SystemExit("Provide --sft-lora-uri or pass --grpo-only")

    image_uri = args.image or default_image_uri(settings, "grpo")
    bucket = settings["GCS_BUCKET"]
    base_output_dir = f"gs://{bucket}/{args.output_prefix.strip('/')}"

    env_vars = merge_training_env_vars(
        wandb_project="aos-grpo",
        wandb_run_name=WANDB_GRPO_RUN_NAME,
        wandb_project_env_key="WANDB_PROJECT_GRPO",
        wandb_group=WANDB_RUN_GROUP,
        wandb_tags=[*WANDB_TAGS, "grpo"],
        extra={"MANIBENCH_GRPO_RENDER": "0"},
    )

    report_to = args.report_to
    if report_to is None:
        report_to = "wandb" if env_vars.get("WANDB_API_KEY") else "none"

    container_args: list[str] = ["--report-to", report_to]
    if args.sft_lora_uri:
        container_args.extend(["--sft-lora-uri", args.sft_lora_uri])
    if args.dataset_uri:
        container_args.extend(["--dataset-uri", args.dataset_uri])
    if args.smoke:
        container_args.append("--smoke")
    if args.grpo_only:
        container_args.append("--grpo-only")

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

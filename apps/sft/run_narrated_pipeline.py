#!/usr/bin/env python3
"""End-to-End Orchestrator Pipeline for AOS Narrated Manim Dataset.

Converts standard Manim trajectories into manim-voiceover scripts using Gemini 2.5 Flash
Batch API, and creates/uploads the resulting dataset to Hugging Face.

Usage:
    export GEMINI_API_KEY=your_gemini_key
    export HF_TOKEN=your_hf_token
    uv run python run_narrated_pipeline.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from narrate_trajectories_batch import (
    DEFAULT_INPUT_TRAJECTORIES,
    DEFAULT_MODEL_ID,
    DEFAULT_OUTPUT_DIR,
    init_environment,
    run_batch_conversion,
)
from upload_narrated_dataset import (
    DEFAULT_REPO_ID,
    upload_narrated_dataset,
)

SFT_ROOT = Path(__file__).resolve().parent


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run full Manim Voiceover batch conversion and HuggingFace dataset upload pipeline"
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=DEFAULT_INPUT_TRAJECTORIES,
        help=f"Input trajectories JSONL path (default: {DEFAULT_INPUT_TRAJECTORIES})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help=f"Gemini model ID (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help=f"HuggingFace dataset repository ID (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--skip-batch",
        action="store_true",
        help="Skip batch generation step (use existing output file)",
    )
    parser.add_argument(
        "--skip-hf",
        action="store_true",
        help="Skip HuggingFace repository upload step",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Batch job status polling interval in seconds (default: 30)",
    )
    return parser


def main() -> int:
    init_environment()
    args = build_arg_parser().parse_args()
    output_dir = args.output_dir.resolve()
    final_dataset_file = output_dir / "manim_narrated_400.jsonl"

    print("==========================================================================")
    print("        AOS Narrated Manim Dataset Pipeline (Gemini Batch + HF)          ")
    print("==========================================================================")

    # 1. Batch API Conversion Step
    if not args.skip_batch:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            print("ERROR: GEMINI_API_KEY is required for batch conversion.", file=sys.stderr)
            return 1

        print(f"\n[Phase 1] Starting Gemini 2.5 Flash Batch Conversion...")
        try:
            final_dataset_file = run_batch_conversion(
                api_key=api_key,
                model_id=args.model_id,
                input_path=args.input_path.resolve(),
                output_dir=output_dir,
                poll_interval=args.poll_interval,
            )
        except Exception as e:
            print(f"ERROR in batch conversion: {e}", file=sys.stderr)
            return 1
    else:
        print(f"\n[Phase 1] Skipped batch generation (--skip-batch set). Using existing dataset: {final_dataset_file}")

    # 2. HuggingFace Upload Step
    if not args.skip_hf:
        print(f"\n[Phase 2] Uploading Narrated Dataset to Hugging Face ({args.repo_id})...")
        try:
            upload_narrated_dataset(
                repo_id=args.repo_id,
                dataset_path=final_dataset_file,
            )
        except Exception as e:
            print(f"ERROR in HuggingFace upload: {e}", file=sys.stderr)
            return 1
    else:
        print("\n[Phase 2] Skipped HuggingFace upload (--skip-hf set).")

    print("\n==========================================================================")
    print("Pipeline completed successfully!")
    if not args.skip_hf:
        print(f"HuggingFace Repo: https://huggingface.co/datasets/{args.repo_id}")
    print(f"Local Dataset: {final_dataset_file}")
    print("==========================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

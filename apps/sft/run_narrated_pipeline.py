#!/usr/bin/env python3
"""End-to-End Orchestrator Pipeline for AOS Narrated Manim Dataset.

Converts standard Manim trajectories into manim-voiceover scripts using
gemini-2.5-flash-lite via the inference.net OpenAI-compatible endpoint,
and publishes the resulting dataset to Hugging Face Hub.

Usage:
    uv run python run_narrated_pipeline.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from narrate_trajectories_batch import (
    DEFAULT_BASE_URL,
    DEFAULT_INPUT_TRAJECTORIES,
    DEFAULT_MODEL_ID,
    DEFAULT_OUTPUT_DIR,
    init_environment,
    run_conversion,
)
from upload_narrated_dataset import (
    DEFAULT_REPO_ID,
    upload_narrated_dataset,
)

SFT_ROOT = Path(__file__).resolve().parent


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run full Manim Voiceover conversion and HuggingFace dataset upload pipeline"
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
        "--base-url",
        default=os.getenv("INFERENCE_NET_BASE_URL", DEFAULT_BASE_URL),
        help=f"OpenAI-compatible base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help=f"Model ID (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("INFERENCE_NET_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY", ""),
        help="API Key (default: loaded from INFERENCE_NET_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY / .env)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent API requests (default: 5)",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming mode",
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help=f"HuggingFace dataset repository ID (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--skip-conversion",
        action="store_true",
        help="Skip generation step (use existing output file)",
    )
    parser.add_argument(
        "--skip-hf",
        action="store_true",
        help="Skip HuggingFace repository upload step",
    )
    return parser


def main() -> int:
    init_environment()
    args = build_arg_parser().parse_args()
    output_dir = args.output_dir.resolve()
    final_dataset_file = output_dir / "manim_narrated_400.jsonl"

    print("==========================================================================")
    print("        AOS Narrated Manim Dataset Pipeline (Inference.net + HF)         ")
    print("==========================================================================")

    # 1. Conversion Step
    if not args.skip_conversion:
        api_key = (
            args.api_key
            or os.getenv("INFERENCE_NET_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("GEMINI_API_KEY", "")
        ).strip()

        if not api_key:
            print("ERROR: Set INFERENCE_NET_API_KEY or OPENAI_API_KEY in .env.", file=sys.stderr)
            return 1

        print(f"\n[Phase 1] Converting Trajectories via {args.base_url} ({args.model_id})...")
        try:
            final_dataset_file = run_conversion(
                api_key=api_key,
                base_url=args.base_url,
                model_id=args.model_id,
                input_path=args.input_path.resolve(),
                output_dir=output_dir,
                concurrency=args.concurrency,
                stream=not args.no_stream,
            )
        except Exception as e:
            print(f"ERROR in conversion: {e}", file=sys.stderr)
            return 1
    else:
        print(f"\n[Phase 1] Skipped conversion (--skip-conversion set). Using existing dataset: {final_dataset_file}")

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

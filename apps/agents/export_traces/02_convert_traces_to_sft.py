#!/usr/bin/env python3
"""
Convert Logfire agent traces to Gemma 4 E2B SFT JSONL.

Produces final_answer (TRL messages) and/or tool_trace (OpenAI tool turns) formats.

Usage:
    cd apps/agents
    uv run python export_traces/02_convert_traces_to_sft.py \
        --input export_traces/manim_traces.jsonl \
        --output-dir export_traces/sft_out \
        --format both

Gemma 4 E2B TRL handoff:
    - Base model: google/gemma-4-E2B
    - Tokenizer: google/gemma-4-E2B-it
    - Dataset field: messages
    - SFTConfig(assistant_only_loss=True, packing=False)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from export_traces.cli import convert_file
from export_traces.config import SFTFormat


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Logfire traces to Gemma 4 E2B SFT JSONL"
    )
    parser.add_argument("--input", required=True, help="Input JSONL from 01_export_traces")
    parser.add_argument(
        "--output-dir",
        default="export_traces/sft_out",
        help="Directory for SFT output files",
    )
    parser.add_argument(
        "--format",
        choices=["final_answer", "tool_trace", "both"],
        default="both",
        help="SFT output format(s)",
    )
    parser.add_argument(
        "--train-split",
        type=float,
        default=0.9,
        help="Train ratio (0-1). Set to 0 to disable split.",
    )
    parser.add_argument("--keep-thinking", action="store_true")
    parser.add_argument("--include-errors", action="store_true")
    parser.add_argument("--include-retries", action="store_true")
    parser.add_argument("--min-chars", type=int, default=0)
    parser.add_argument("--max-chars", type=int, default=None)
    parser.add_argument("--max-tool-result-chars", type=int, default=8192)
    parser.add_argument("--no-deduplicate", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = base / input_path

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = base / output_dir

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    train_split = args.train_split if args.train_split > 0 else None
    sft_format: SFTFormat = args.format  # type: ignore[assignment]

    convert_file(
        input_path,
        output_dir,
        sft_format=sft_format,
        keep_thinking=args.keep_thinking,
        include_errors=args.include_errors,
        include_retries=args.include_retries,
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        max_tool_result_chars=args.max_tool_result_chars,
        deduplicate=not args.no_deduplicate,
        train_split=train_split,
        seed=args.seed,
        validate=not args.no_validate,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

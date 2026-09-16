#!/usr/bin/env python3
"""Split train.jsonl into chunks of N examples each (default 10).

Usage:
    uv run python split_train_chunks.py
    uv run python split_train_chunks.py --chunk-size 10 --output-dir ./data/train_chunks_10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_FILE = SCRIPT_DIR / "data" / "train.jsonl"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "data" / "train_chunks_10"


def split_jsonl(input_file: Path, output_dir: Path, chunk_size: int = 10) -> list[Path]:
    if not input_file.is_file():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]

    total_examples = len(lines)
    num_chunks = (total_examples + chunk_size - 1) // chunk_size
    padding = max(2, len(str(num_chunks)))

    print(f"Splitting {total_examples} examples from '{input_file.name}' into chunks of {chunk_size}...")
    created_files: list[Path] = []

    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * chunk_size
        end_idx = min(start_idx + chunk_size, total_examples)
        chunk_lines = lines[start_idx:end_idx]

        chunk_filename = f"train_part_{chunk_idx + 1:0{padding}d}.jsonl"
        chunk_path = output_dir / chunk_filename

        with open(chunk_path, "w", encoding="utf-8") as out_f:
            for l in chunk_lines:
                out_f.write(l.strip() + "\n")

        created_files.append(chunk_path)
        print(f"  ✔ Created {chunk_filename} (examples {start_idx + 1} - {end_idx}, count: {len(chunk_lines)})")

    print(f"\nTotal chunk files created: {len(created_files)} in {output_dir}")
    return created_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Split train.jsonl into chunks of N examples")
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT_FILE, help="Path to input train.jsonl")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Destination directory for chunks")
    parser.add_argument("--chunk-size", type=int, default=10, help="Number of examples per chunk (default: 10)")
    args = parser.parse_args()

    split_jsonl(args.input_file, args.output_dir, args.chunk_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

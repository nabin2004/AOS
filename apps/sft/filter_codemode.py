#!/usr/bin/env python3
"""Filter tool_trace / messages JSONL rows that violate the CodeMode contract.

Drops assistant ``run_code`` turns with star imports, nested run_code calls,
or multi-line single/double-quoted string literals.
Writes a sibling ``*.codemode_clean.jsonl`` by default (does not overwrite).

Usage (from apps/sft):

    uv run python filter_codemode.py \\
      ../agents/export_traces/coder_sft/tool_trace.train.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from codemode_contract import messages_violate_codemode


def filter_jsonl(input_path: Path, output_path: Path) -> tuple[int, int]:
    kept = 0
    dropped = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        input_path.open("r", encoding="utf-8") as src,
        output_path.open("w", encoding="utf-8") as dst,
    ):
        for line in src:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            messages = row.get("messages")
            if messages_violate_codemode(
                messages if isinstance(messages, list) else None
            ):
                dropped += 1
                continue
            clean = {k: v for k, v in row.items() if not str(k).startswith("_")}
            dst.write(json.dumps(clean, ensure_ascii=False) + "\n")
            kept += 1
    return kept, dropped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drop CodeMode contract violations from SFT JSONL"
    )
    parser.add_argument("input", type=Path, help="Input messages/tool_trace JSONL")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: <input stem>.codemode_clean.jsonl)",
    )
    args = parser.parse_args()
    input_path = args.input.resolve()
    if not input_path.is_file():
        raise SystemExit(f"Input not found: {input_path}")
    output_path = (
        args.output.resolve()
        if args.output
        else input_path.with_name(f"{input_path.stem}.codemode_clean.jsonl")
    )
    kept, dropped = filter_jsonl(input_path, output_path)
    total = kept + dropped
    print(f"Input:   {input_path}")
    print(f"Output:  {output_path}")
    print(f"Kept:    {kept}")
    print(f"Dropped: {dropped} (codemode contract violations)")
    print(f"Total:   {total}")


if __name__ == "__main__":
    main()

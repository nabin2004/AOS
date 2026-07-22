#!/usr/bin/env python3
"""Export Code Agent Logfire traces and convert to SFT JSONL (tool_trace + final_answer).

Primary finetune format is tool_trace (preserves tool / CodeMode calls).
Local per-run traces also live under workspace/coder_runs/*/traces/messages.json.

Usage (from apps/agents):

    # Needs LOGFIRE_READ_TOKEN in export_traces/.env or environment
    uv run python export_coder_sft.py --days 30

    # Export only (no convert)
    uv run python export_coder_sft.py --days 7 --export-only

    # Convert an existing export
    uv run python export_coder_sft.py --skip-export \\
        --input export_traces/coder_traces.jsonl
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

AGENTS_ROOT = Path(__file__).resolve().parent
EXPORT_DIR = AGENTS_ROOT / "export_traces"
DEFAULT_TRACES = EXPORT_DIR / "coder_traces.jsonl"
DEFAULT_SFT_OUT = EXPORT_DIR / "coder_sft"
AGENT_NAME = "Code Agent"


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=AGENTS_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export + convert Code Agent traces for tool-calling SFT"
    )
    parser.add_argument("--days", type=int, default=30, help="Logfire lookback days")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_TRACES,
        help="Exported spans JSONL path",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_SFT_OUT,
        help="SFT JSONL output directory",
    )
    parser.add_argument(
        "--format",
        choices=("final_answer", "tool_trace", "both"),
        default="both",
        help="SFT format (tool_trace recommended for Code Agent)",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only export spans from Logfire",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip Logfire export; convert --input only",
    )
    args = parser.parse_args()

    if not args.skip_export:
        args.input.parent.mkdir(parents=True, exist_ok=True)
        rc = _run(
            [
                sys.executable,
                str(EXPORT_DIR / "01_export_traces.py"),
                "--days",
                str(args.days),
                "--agent-name",
                AGENT_NAME,
                "--output",
                str(args.input),
            ]
        )
        if rc != 0:
            return rc
        if args.export_only:
            print(f"Exported Code Agent spans → {args.input}")
            return 0

    if not args.input.is_file():
        print(f"Missing export file: {args.input}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rc = _run(
        [
            sys.executable,
            str(EXPORT_DIR / "02_convert_traces_to_sft.py"),
            "--input",
            str(args.input),
            "--output-dir",
            str(args.output_dir),
            "--format",
            args.format,
        ]
    )
    if rc == 0:
        print(
            f"Code Agent SFT written under {args.output_dir} "
            f"(prefer tool_trace*.jsonl for tool-use finetuning)"
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

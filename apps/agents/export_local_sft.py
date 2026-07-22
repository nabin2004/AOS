#!/usr/bin/env python3
"""Export local Code Agent trajectories to SFT JSONL (no Logfire required).

Reads training_data/trajectories.jsonl (or scans workspace/coder_runs/) and
writes tool_trace / final_answer JSONL under export_traces/coder_sft/.

Usage (from apps/agents):

    uv run python export_local_sft.py
    uv run python export_local_sft.py --scan-workspace
    uv run python export_local_sft.py --format tool_trace --train-split 0.9
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

AGENTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENTS_ROOT))

from export_traces.config import SFTFormat
from export_traces.converters.tool_trace import convert_normalized_messages
from export_traces.otel_messages import normalize_model_messages
from export_traces.trajectory_select import (
    TrajectorySelectionResult,
    select_trajectories,
)
from export_traces.validate import (
    ValidationReport,
    split_train_val,
    validate_file,
    write_jsonl,
)
from pydantic_ai.messages import ModelMessagesTypeAdapter

DEFAULT_INPUT = AGENTS_ROOT / "training_data" / "trajectories.jsonl"
DEFAULT_OUTPUT = AGENTS_ROOT / "export_traces" / "coder_sft"
WORKSPACE_ROOT = AGENTS_ROOT / "workspace" / "coder_runs"


@dataclass
class LocalConversionResult:
    final_answer: list[dict[str, Any]] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: list[dict[str, Any]] = field(default_factory=list)
    selection: TrajectorySelectionResult = field(
        default_factory=TrajectorySelectionResult
    )
    skipped_conversion: int = 0


def load_trajectory_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def scan_workspace_trajectories() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not WORKSPACE_ROOT.is_dir():
        return records
    for trajectory_path in sorted(WORKSPACE_ROOT.glob("*/traces/trajectory.json")):
        records.append(json.loads(trajectory_path.read_text(encoding="utf-8")))
    return records


def _load_run_messages(record: dict[str, Any]) -> list[Any] | None:
    run_dir = record.get("run_dir")
    if not run_dir:
        return None
    messages_path = AGENTS_ROOT / run_dir / "traces" / "messages.json"
    if not messages_path.is_file():
        return None
    return ModelMessagesTypeAdapter.validate_json(messages_path.read_bytes())


def convert_trajectory_record(
    record: dict[str, Any],
    *,
    sft_format: SFTFormat,
    keep_thinking: bool,
    max_tool_result_chars: int | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    meta = {
        "run_dir": record.get("run_dir"),
        "prompt_index": record.get("prompt_index"),
        "success": record.get("success"),
        "timestamp": record.get("timestamp"),
        "agent_name": "Code Agent",
    }
    user_prompt = str(record.get("user_prompt", "")).strip()

    fa_row: dict[str, Any] | None = None
    tt_row: dict[str, Any] | None = None

    if sft_format in ("final_answer", "both"):
        assistant = record.get("final_code") or record.get("summary")
        if user_prompt and assistant:
            fa_row = {
                "messages": [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": str(assistant)},
                ]
            }

    if sft_format in ("tool_trace", "both"):
        raw_messages = _load_run_messages(record)
        if raw_messages:
            normalized = normalize_model_messages(raw_messages)
            tt_row = convert_normalized_messages(
                normalized,
                keep_thinking=keep_thinking,
                max_tool_result_chars=max_tool_result_chars,
                user_prompt_override=user_prompt or None,
            )

    return fa_row, tt_row, meta


def convert_trajectories_to_sft(
    records: list[dict[str, Any]],
    *,
    sft_format: SFTFormat = "both",
    keep_thinking: bool = False,
    include_errors: bool = False,
    max_tool_result_chars: int | None = 8192,
    deduplicate: bool = True,
) -> LocalConversionResult:
    selection = select_trajectories(
        records,
        include_errors=include_errors,
        deduplicate=deduplicate,
    )
    result = LocalConversionResult(selection=selection)

    for record in selection.selected:
        fa_row, tt_row, meta = convert_trajectory_record(
            record,
            sft_format=sft_format,
            keep_thinking=keep_thinking,
            max_tool_result_chars=max_tool_result_chars,
        )
        if fa_row:
            fa_row["_metadata"] = meta
            result.final_answer.append(fa_row)
        if tt_row:
            tt_row["_metadata"] = meta
            result.tool_trace.append(tt_row)
        if fa_row or tt_row:
            result.metadata.append(meta)
        else:
            result.skipped_conversion += 1

    return result


def write_local_sft_outputs(
    result: LocalConversionResult,
    output_dir: Path,
    *,
    sft_format: SFTFormat = "both",
    train_split: float | None = None,
    seed: int = 42,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    def _write_split(name: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        if train_split is not None and 0.0 < train_split < 1.0:
            train_rows, val_rows = split_train_val(rows, train_split, seed=seed)
            train_path = output_dir / f"{name}.train.jsonl"
            val_path = output_dir / f"{name}.val.jsonl"
            write_jsonl(train_path, train_rows)
            write_jsonl(val_path, val_rows)
            written[f"{name}.train"] = train_path
            written[f"{name}.val"] = val_path
        else:
            path = output_dir / f"{name}.jsonl"
            write_jsonl(path, rows)
            written[name] = path

    if sft_format in ("final_answer", "both"):
        _write_split("final_answer", result.final_answer)
    if sft_format in ("tool_trace", "both"):
        _write_split("tool_trace", result.tool_trace)

    if result.metadata:
        meta_path = output_dir / "metadata.jsonl"
        with meta_path.open("w", encoding="utf-8") as f:
            for row in result.metadata:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        written["metadata"] = meta_path

    return written


def print_local_report(
    result: LocalConversionResult,
    *,
    sft_format: SFTFormat,
    written_paths: dict[str, Path],
    source: str,
) -> None:
    stats = result.selection.drop_stats.to_dict()
    print(f"\nSource: {source}")
    print(f"Selection: {len(result.selection.selected)} trajectories selected")
    print(f"Dropped: {json.dumps(stats)}")
    print(f"Skipped during conversion: {result.skipped_conversion}")

    if sft_format in ("final_answer", "both"):
        print(f"Final answer examples: {len(result.final_answer)}")
    if sft_format in ("tool_trace", "both"):
        print(f"Tool trace examples: {len(result.tool_trace)}")
    print(f"Metadata rows: {len(result.metadata)}")

    print("\nWritten files:")
    for name, path in sorted(written_paths.items()):
        print(f"  {name}: {path}")


def convert_local_file(
    input_path: Path | None,
    output_dir: Path,
    *,
    scan_workspace: bool = False,
    sft_format: SFTFormat = "both",
    keep_thinking: bool = False,
    include_errors: bool = False,
    max_tool_result_chars: int | None = 8192,
    deduplicate: bool = True,
    train_split: float | None = 0.9,
    seed: int = 42,
    validate: bool = True,
) -> tuple[LocalConversionResult, dict[str, Path], dict[str, ValidationReport]]:
    if scan_workspace:
        records = scan_workspace_trajectories()
        source = str(WORKSPACE_ROOT)
    else:
        if input_path is None or not input_path.is_file():
            raise FileNotFoundError(f"Trajectory file not found: {input_path}")
        records = load_trajectory_jsonl(input_path)
        source = str(input_path)

    print(f"Read {len(records)} trajectory records from {source}")

    result = convert_trajectories_to_sft(
        records,
        sft_format=sft_format,
        keep_thinking=keep_thinking,
        include_errors=include_errors,
        max_tool_result_chars=max_tool_result_chars,
        deduplicate=deduplicate,
    )

    written = write_local_sft_outputs(
        result,
        output_dir,
        sft_format=sft_format,
        train_split=train_split,
        seed=seed,
    )
    print_local_report(
        result, sft_format=sft_format, written_paths=written, source=source
    )

    reports: dict[str, ValidationReport] = {}
    if validate:
        print("\nValidation:")
        for key, path in written.items():
            if "final_answer" in key:
                report = validate_file(path, format_name="final_answer")
                reports[key] = report
                print(f"  {key}: {report.valid}/{report.total} valid")
            elif "tool_trace" in key:
                report = validate_file(path, format_name="tool_trace")
                reports[key] = report
                print(f"  {key}: {report.valid}/{report.total} valid")

    return result, written, reports


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert local Code Agent trajectories to SFT JSONL"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Global trajectories JSONL (default: {DEFAULT_INPUT.name})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"SFT output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--scan-workspace",
        action="store_true",
        help="Scan workspace/coder_runs/*/traces/trajectory.json instead of global JSONL",
    )
    parser.add_argument(
        "--format",
        choices=("final_answer", "tool_trace", "both"),
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
    parser.add_argument("--max-tool-result-chars", type=int, default=8192)
    parser.add_argument("--no-deduplicate", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    input_path = None if args.scan_workspace else args.input.resolve()
    output_dir = args.output_dir.resolve()
    train_split = args.train_split if args.train_split > 0 else None
    sft_format: SFTFormat = args.format  # type: ignore[assignment]

    try:
        convert_local_file(
            input_path,
            output_dir,
            scan_workspace=args.scan_workspace,
            sft_format=sft_format,
            keep_thinking=args.keep_thinking,
            include_errors=args.include_errors,
            max_tool_result_chars=args.max_tool_result_chars,
            deduplicate=not args.no_deduplicate,
            train_split=train_split,
            seed=args.seed,
            validate=not args.no_validate,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"\nLocal SFT written under {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

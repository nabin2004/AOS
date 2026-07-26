from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from export_traces.codemode_contract import tool_trace_violates_codemode
from export_traces.config import SFTFormat
from export_traces.converters.final_answer import convert_final_answer
from export_traces.converters.tool_trace import convert_tool_trace
from export_traces.logfire_export import load_spans
from export_traces.otel_messages import metadata_from_span
from export_traces.trace_select import SelectionResult, select_spans
from export_traces.validate import (
    ValidationReport,
    split_train_val,
    validate_file,
    write_jsonl,
)


@dataclass
class ConversionResult:
    final_answer: list[dict[str, Any]] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: list[dict[str, Any]] = field(default_factory=list)
    selection: SelectionResult = field(default_factory=SelectionResult)
    skipped_conversion: int = 0
    skipped_codemode: int = 0


def convert_spans_to_sft(
    spans: list[dict[str, Any]],
    *,
    sft_format: SFTFormat = "both",
    keep_thinking: bool = False,
    include_errors: bool = False,
    include_retries: bool = False,
    min_chars: int = 0,
    max_chars: int | None = None,
    max_tool_result_chars: int | None = 8192,
    deduplicate: bool = True,
) -> ConversionResult:
    selection = select_spans(
        spans,
        include_errors=include_errors,
        include_retries=include_retries,
        min_chars=min_chars,
        max_chars=max_chars,
        deduplicate=deduplicate,
    )

    result = ConversionResult(selection=selection)
    spans_to_convert = list(selection.selected_spans)
    if include_retries:
        spans_to_convert.extend(selection.retry_spans)

    seen_conversion: set[tuple[str, str]] = set()

    for span in spans_to_convert:
        span_id = str(span.get("span_id", ""))
        trace_id = str(span.get("trace_id", ""))
        key = (trace_id, span_id)
        if key in seen_conversion:
            continue
        seen_conversion.add(key)

        meta = metadata_from_span(span)

        fa_row = None
        tt_row = None

        if sft_format in ("final_answer", "both"):
            fa_row = convert_final_answer(span, keep_thinking=keep_thinking)
            if fa_row:
                fa_row["_metadata"] = meta
                result.final_answer.append(fa_row)

        if sft_format in ("tool_trace", "both"):
            tt_row = convert_tool_trace(
                span,
                keep_thinking=keep_thinking,
                max_tool_result_chars=max_tool_result_chars,
            )
            if tt_row and tool_trace_violates_codemode(tt_row):
                result.skipped_codemode += 1
                tt_row = None
            if tt_row:
                tt_row["_metadata"] = meta
                result.tool_trace.append(tt_row)

        if fa_row or tt_row:
            result.metadata.append(meta)
        else:
            result.skipped_conversion += 1

    return result


def write_sft_outputs(
    result: ConversionResult,
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


def print_conversion_report(
    result: ConversionResult,
    *,
    sft_format: SFTFormat,
    written_paths: dict[str, Path],
) -> None:
    stats = result.selection.drop_stats.to_dict()
    print(f"\nSelection: {len(result.selection.selected_spans)} spans selected")
    print(f"Dropped: {json.dumps(stats)}")
    print(f"Skipped during conversion: {result.skipped_conversion}")
    if result.skipped_codemode:
        print(f"Skipped CodeMode star-import violations: {result.skipped_codemode}")

    if sft_format in ("final_answer", "both"):
        print(f"Final answer examples: {len(result.final_answer)}")
    if sft_format in ("tool_trace", "both"):
        print(f"Tool trace examples: {len(result.tool_trace)}")
    print(f"Metadata rows: {len(result.metadata)}")

    agent_counts: dict[str, int] = {}
    for row in result.metadata:
        agent = row.get("agent_name", "Unknown")
        agent_counts[agent] = agent_counts.get(agent, 0) + 1
    if agent_counts:
        print("\nAgent distribution:")
        total = sum(agent_counts.values())
        for agent, count in sorted(agent_counts.items()):
            pct = count / total * 100 if total else 0
            print(f"  {agent}: {count} ({pct:.1f}%)")

    print("\nWritten files:")
    for name, path in sorted(written_paths.items()):
        print(f"  {name}: {path}")


def convert_file(
    input_path: Path,
    output_dir: Path,
    *,
    sft_format: SFTFormat = "both",
    keep_thinking: bool = False,
    include_errors: bool = False,
    include_retries: bool = False,
    min_chars: int = 0,
    max_chars: int | None = None,
    max_tool_result_chars: int | None = 8192,
    deduplicate: bool = True,
    train_split: float | None = 0.9,
    seed: int = 42,
    validate: bool = True,
) -> tuple[ConversionResult, dict[str, Path], dict[str, ValidationReport]]:
    spans = load_spans(input_path)
    print(f"Read {len(spans)} spans from {input_path}")

    result = convert_spans_to_sft(
        spans,
        sft_format=sft_format,
        keep_thinking=keep_thinking,
        include_errors=include_errors,
        include_retries=include_retries,
        min_chars=min_chars,
        max_chars=max_chars,
        max_tool_result_chars=max_tool_result_chars,
        deduplicate=deduplicate,
    )

    written = write_sft_outputs(
        result,
        output_dir,
        sft_format=sft_format,
        train_split=train_split,
        seed=seed,
    )
    print_conversion_report(result, sft_format=sft_format, written_paths=written)

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

#!/usr/bin/env python3
"""Audit tool_trace JSONL rows for CodeMode contract violations.

Usage (from apps/sft):

    uv run python audit_codemode_training.py
    uv run python audit_codemode_training.py --train ../agents/export_traces/coder_sft/tool_trace.train.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from codemode_contract import codemode_message_violations, extract_run_code_body

SFT_ROOT = Path(__file__).resolve().parent
APPS_ROOT = SFT_ROOT.parent
DEFAULT_TRAIN = (
    APPS_ROOT / "agents" / "export_traces" / "coder_sft" / "tool_trace.train.jsonl"
)
DEFAULT_VAL = (
    APPS_ROOT / "agents" / "export_traces" / "coder_sft" / "tool_trace.val.jsonl"
)
DIAG = SFT_ROOT / "diagnostics"


def _first_user_preview(messages: list[dict]) -> str:
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            text = str(msg.get("content") or "").strip()
            if text:
                return text[:120].replace("\n", " ")
    return ""


def audit_file(path: Path) -> dict:
    violation_counts: Counter[str] = Counter()
    rows_with_violations = 0
    total = 0
    samples: list[dict] = []

    with path.open(encoding="utf-8") as handle:
        for row_idx, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            messages = row.get("messages")
            if not isinstance(messages, list):
                continue
            total += 1
            violations = codemode_message_violations(messages)
            if not violations:
                continue
            rows_with_violations += 1
            for code in violations:
                violation_counts[code] += 1
            if len(samples) < 20:
                preview = ""
                for msg in messages:
                    if msg.get("role") != "assistant":
                        continue
                    for tc in msg.get("tool_calls") or []:
                        fn = tc.get("function") or {}
                        if fn.get("name") != "run_code":
                            continue
                        body = extract_run_code_body(fn.get("arguments")) or ""
                        preview = body[:160].replace("\n", "\\n")
                        break
                samples.append(
                    {
                        "row": row_idx,
                        "violations": violations,
                        "user_preview": _first_user_preview(messages),
                        "code_preview": preview,
                    }
                )

    return {
        "path": str(path),
        "total_rows": total,
        "rows_with_violations": rows_with_violations,
        "violation_counts": dict(violation_counts),
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit CodeMode violations in tool_trace JSONL"
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--val", type=Path, default=DEFAULT_VAL)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON report (default: diagnostics/codemode_training_audit_<ts>.json)",
    )
    args = parser.parse_args()

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "datasets": [audit_file(args.train)],
    }
    if args.val.exists():
        report["datasets"].append(audit_file(args.val))

    out = (
        args.out
        or DIAG
        / f"codemode_training_audit_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for dataset in report["datasets"]:
        print(
            f"{dataset['path']}: {dataset['rows_with_violations']}/{dataset['total_rows']} "
            f"rows with violations -> {dataset['violation_counts']}"
        )
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

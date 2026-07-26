from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from export_traces.codemode_contract import tool_trace_violates_codemode


REQUIRED_ROLES_FINAL = {"user", "assistant"}
REQUIRED_ROLES_TOOL = {"user", "assistant"}


@dataclass
class ValidationReport:
    format_name: str
    total: int = 0
    valid: int = 0
    invalid: int = 0
    errors: Counter[str] = field(default_factory=Counter)
    agent_counts: Counter[str] = field(default_factory=Counter)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format_name,
            "total": self.total,
            "valid": self.valid,
            "invalid": self.invalid,
            "errors": dict(self.errors),
            "agent_counts": dict(self.agent_counts),
        }


def validate_messages_row(row: dict[str, Any], *, format_name: str) -> list[str]:
    errors: list[str] = []
    messages = row.get("messages")
    if not isinstance(messages, list) or not messages:
        errors.append("missing_messages")
        return errors

    roles = {m.get("role") for m in messages if isinstance(m, dict)}
    if not REQUIRED_ROLES_FINAL.issubset(roles):
        errors.append("missing_required_roles")

    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            errors.append(f"message_{i}_not_dict")
            continue
        role = msg.get("role")
        if role not in ("system", "user", "assistant", "tool"):
            errors.append(f"message_{i}_invalid_role")
        if role in ("system", "user") and not str(msg.get("content", "")).strip():
            errors.append(f"message_{i}_empty_content")
        if role == "assistant":
            content = msg.get("content")
            tool_calls = msg.get("tool_calls")
            if format_name == "final_answer":
                if not str(content or "").strip():
                    errors.append(f"message_{i}_empty_assistant")
            elif format_name == "tool_trace":
                if content is None and not tool_calls:
                    errors.append(f"message_{i}_empty_assistant")
        if role == "tool":
            if not msg.get("tool_call_id"):
                errors.append(f"message_{i}_missing_tool_call_id")
            if not str(msg.get("content", "")).strip() and msg.get("content") != "":
                errors.append(f"message_{i}_empty_tool_content")

    if format_name == "tool_trace":
        errors.extend(tool_trace_violates_codemode(row))

    return errors


def validate_file(path: Path, *, format_name: str) -> ValidationReport:
    report = ValidationReport(format_name=format_name)
    if not path.exists():
        return report

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            report.total += 1
            row = json.loads(line)
            errors = validate_messages_row(row, format_name=format_name)
            meta_agent = None
            if isinstance(row.get("_metadata"), dict):
                meta_agent = row["_metadata"].get("agent_name")
            if meta_agent:
                report.agent_counts[meta_agent] += 1
            if errors:
                report.invalid += 1
                for err in errors:
                    report.errors[err] += 1
            else:
                report.valid += 1
    return report


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            clean = {k: v for k, v in row.items() if not k.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")


def split_train_val(
    rows: list[dict[str, Any]],
    train_ratio: float,
    *,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not rows:
        return [], []
    shuffled = list(rows)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    split_idx = int(len(shuffled) * train_ratio)
    if split_idx == 0 and len(shuffled) > 1:
        split_idx = 1
    if split_idx == len(shuffled) and len(shuffled) > 1:
        split_idx = len(shuffled) - 1
    return shuffled[:split_idx], shuffled[split_idx:]

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrajectoryDropStats:
    failed: int = 0
    duplicate: int = 0

    def to_dict(self) -> dict[str, int]:
        return {"failed": self.failed, "duplicate": self.duplicate}


@dataclass
class TrajectorySelectionResult:
    selected: list[dict[str, Any]] = field(default_factory=list)
    dropped: list[dict[str, Any]] = field(default_factory=list)
    drop_stats: TrajectoryDropStats = field(default_factory=TrajectoryDropStats)


def prompt_hash(record: dict[str, Any]) -> str | None:
    prompt = str(record.get("user_prompt", "")).strip()
    if not prompt:
        return None
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def trajectory_score(record: dict[str, Any]) -> tuple[int, int, str]:
    """Higher is better: (success, -tool_steps, timestamp)."""
    success = 1 if record.get("success") else 0
    trajectory = record.get("trajectory") or []
    tool_steps = -len(trajectory)
    timestamp = str(record.get("timestamp") or "")
    return (success, tool_steps, timestamp)


def select_trajectories(
    records: list[dict[str, Any]],
    *,
    include_errors: bool = False,
    deduplicate: bool = True,
) -> TrajectorySelectionResult:
    """Keep the shortest successful trajectory per unique user_prompt."""
    result = TrajectorySelectionResult()
    groups: dict[str, list[dict[str, Any]]] = {}

    for record in records:
        if not include_errors and not record.get("success"):
            result.drop_stats.failed += 1
            result.dropped.append(record)
            continue

        key = prompt_hash(record)
        if key is None:
            result.drop_stats.failed += 1
            result.dropped.append(record)
            continue
        groups.setdefault(key, []).append(record)

    seen_hashes: set[str] = set()
    for key, group in groups.items():
        best = max(group, key=trajectory_score)
        if deduplicate:
            if key in seen_hashes:
                result.drop_stats.duplicate += len(group)
                result.dropped.extend(group)
                continue
            seen_hashes.add(key)

        result.selected.append(best)
        if deduplicate and len(group) > 1:
            result.drop_stats.duplicate += len(group) - 1
            for record in group:
                if record is not best:
                    result.dropped.append(record)

    return result

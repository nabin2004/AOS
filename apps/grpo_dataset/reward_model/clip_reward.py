from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ClipAlignmentResult:
    score: float
    per_event: dict[str, float]


def clip_alignment_score(
    visual_events: dict[str, Any],
    window_to_similarity: dict[str, float],
) -> ClipAlignmentResult:
    total = 0.0
    denom = 0.0
    per_event: dict[str, float] = {}

    for event in visual_events.get("events", []):
        event_id = event["event_id"]
        weight = float(event.get("weight", 0.0))
        sim = float(window_to_similarity.get(event_id, 0.0))
        sim = max(0.0, min(1.0, sim))

        per_event[event_id] = sim
        total += weight * sim
        denom += weight

    return ClipAlignmentResult(score=(total / denom if denom else 0.0), per_event=per_event)

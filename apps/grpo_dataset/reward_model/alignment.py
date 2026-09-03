from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AlignmentResult:
    score: float
    per_event: dict[str, float]


def keyword_alignment_score(code: str, visual_events: dict[str, Any]) -> AlignmentResult:
    per_event: dict[str, float] = {}
    total = 0.0
    denom = 0.0

    for event in visual_events.get("events", []):
        event_id = event["event_id"]
        keywords = event.get("keyword_bank", [])
        weight = float(event.get("weight", 0.0))

        if not keywords:
            event_score = 0.0
        else:
            hit_count = sum(1 for kw in keywords if kw in code)
            event_score = hit_count / len(keywords)

        per_event[event_id] = event_score
        total += weight * event_score
        denom += weight

    final_score = total / denom if denom else 0.0
    return AlignmentResult(score=final_score, per_event=per_event)

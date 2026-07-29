"""Prompt shaping for the Manim coder — especially local Ollama/GGUF."""

from __future__ import annotations

from typing import Any

_LOCAL_PLAN_KEYS = (
    "topic",
    "subject",
    "greeting",
    "opener",
    "needed_formulas",
    "class_names",
    "does_it_needs_3d",
    "assumptions",
    "objectives",
    "learning_outcomes",
)

_LIST_CAPS: dict[str, int] = {
    "needed_formulas": 6,
    "assumptions": 4,
    "objectives": 5,
    "learning_outcomes": 4,
    "class_names": 3,
}


def plan_to_payload(plan: Any) -> dict[str, Any]:
    if isinstance(plan, dict):
        return plan
    if hasattr(plan, "model_dump"):
        return plan.model_dump(mode="json")
    return {"raw": str(plan)}


def compact_plan_for_local_coder(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep teaching essentials; drop verbose planner metadata for Ollama context."""
    compact = {k: payload[k] for k in _LOCAL_PLAN_KEYS if k in payload}
    for key, cap in _LIST_CAPS.items():
        if key in compact and isinstance(compact[key], list):
            compact[key] = compact[key][:cap]
    opener = compact.get("opener")
    if isinstance(opener, str) and len(opener) > 400:
        compact["opener"] = opener[:397] + "..."
    beats = payload.get("storyboard_beats")
    if isinstance(beats, list) and beats:
        compact["beats"] = [
            {
                "title": b.get("title", ""),
                "narration": str(b.get("narration", ""))[:180],
                "visual": str(b.get("visual", ""))[:180],
            }
            for b in beats[:8]
        ]
    return compact


LOCAL_CODER_CODEMODE_HINT = (
    "Call tools ONLY via run_code (CodeMode). "
    "Inside run_code these already exist — call with await, never define/import/mock them: "
    "manim_write, compile_manim_code, manim_read, synthesize_narration. "
    "Wrap Manim source in triple-quoted strings; never put from manim import * "
    "at the top level of run_code.\n"
)

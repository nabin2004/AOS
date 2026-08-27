"""Prompt shaping for the Manim coder — especially local Ollama/GGUF."""

from __future__ import annotations

import json
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

CODER_SCRIPT_HINT = (
    "Implement teaching_script narration verbatim (or very close). "
    "Do not invent filler voiceover. Map each beat's visual to Manim. "
    "Use <bookmark mark='…'/> only where bookmark_marks are set. "
    "Narration must teach; never copy on-screen Tex into speech.\n"
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
    script = payload.get("teaching_script")
    if isinstance(script, dict) and script.get("beats"):
        throughline = str(script.get("throughline") or "")
        compact["teaching_script"] = {
            "scene_class_name": script.get("scene_class_name") or "",
            "throughline": throughline[:400],
            "beats": [
                {
                    "id": b.get("id", ""),
                    "takeaway": b.get("takeaway", ""),
                    "visual": b.get("visual", ""),
                    "narration": str(b.get("narration") or ""),
                    "bookmark_marks": b.get("bookmark_marks") or [],
                }
                for b in (script.get("beats") or [])[:10]
                if isinstance(b, dict)
            ],
        }
        return compact
    beats = payload.get("storyboard_beats")
    if isinstance(beats, list) and beats:
        compact["beats"] = [
            {
                "title": b.get("title", ""),
                "narration": str(b.get("narration", "")),
                "visual": str(b.get("visual", "")),
            }
            for b in beats[:8]
            if isinstance(b, dict)
        ]
    return compact


LOCAL_CODER_CODEMODE_HINT = (
    "Call tools ONLY via run_code (CodeMode): wrap Manim source in triple-quoted "
    "strings and await manim_write / compile_manim_code. "
    "Never put from manim import * at the top level of run_code.\n"
)


def build_coder_user_prompt(
    *,
    topic: str,
    subject: str,
    output_dir: Any,
    plan_payload: dict[str, Any],
    compact: bool = False,
    include_codemode_hint: bool = False,
) -> str:
    payload = dict(plan_payload)
    script_payload = payload.get("teaching_script")
    if compact:
        payload = compact_plan_for_local_coder(payload)
    plan_text = json.dumps(payload, indent=2)
    bits = [
        f"Topic: {topic}",
        f"Subject: {subject}",
        f"output_dir: {output_dir}",
        f"Use output_dir={output_dir!s} for every manim_write / compile_manim_code / "
        f"manim_read / synthesize_narration call.",
    ]
    if include_codemode_hint:
        bits.append(LOCAL_CODER_CODEMODE_HINT.rstrip("\n"))
    if script_payload:
        bits.append(CODER_SCRIPT_HINT.rstrip("\n"))
    bits.append(f"Plan:\n{plan_text}")
    return "\n".join(bits) + "\n"


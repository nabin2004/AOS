"""Prompt shaping for the Manim coder — especially local Ollama/GGUF."""

from __future__ import annotations

import json
from typing import Any

from cinematic_hints import CINEMATIC_HINT_LEGEND, annotate_teaching_script
from video_templates import get_template_for_duration

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
    "VOICEOVER, PACING & PEDAGOGY CONTRACT (CRITICAL):\n"
    "1. DUAL INHERITANCE (CRITICAL FOR 3D & CAMERA MOVEMENT):\n"
    "   - Whenever using 3D axes (ThreeDAxes), camera moves (move_camera), or rotations (begin_ambient_camera_rotation),\n"
    "     your scene MUST subclass both: `class MyScene(VoiceoverScene, ThreeDScene):`.\n"
    "   - This gives access to 3D coordinate projection AND automated voiceover speech synthesis.\n"
    "2. FLAWLESS AUDIO SYNCHRONIZATION:\n"
    "   - Every animation beat MUST be wrapped inside `with self.voiceover(text=\"...\") as tracker:` blocks.\n"
    "   - Tie visual animation durations directly to tracker.duration! E.g. `self.play(..., run_time=tracker.duration)`.\n"
    "   - NEVER put hardcoded self.wait(...) inside a voiceover block. Let the voiceover tracker determine the beat length!\n"
    "3. SCREEN HYGIENE (NO SPATIAL OVERLAPS):\n"
    "   - When transitioning to a new coordinate plane, 3D axes, or visual section, explicitly clear the board:\n"
    "     `self.play(FadeOut(Group(*self.mobjects)))` or fade out previous equations/text.\n"
    "   - NEVER create 3D axes directly over equations in the center of the screen!\n"
    "4. DYNAMIC UPDATERS & STATE MANAGEMENT:\n"
    "   - Use ValueTracker and always_redraw() for continuously updating math, tangent lines, and indicators.\n"
    "   - For chaotic systems or ODEs (e.g. Lorenz Attractor), compute numerical trajectories in numpy:\n"
    "     sigma, rho, beta = 10.0, 28.0, 8.0/3.0\n"
    "     dt, x, y, z = 0.01, 0.1, 0.1, 0.1\n"
    "     pts = [axes.c2p(x, y, z)]\n"
    "     for _ in range(2000):\n"
    "         dx = sigma*(y - x)*dt; dy = (x*(rho - z) - y)*dt; dz = (x*y - beta*z)*dt\n"
    "         x += dx; y += dy; z += dz\n"
    "         pts.append(axes.c2p(x, y, z))\n"
    "     curve = VMobject(color=BLUE).set_points_smoothly(pts)\n"
    "   - For chaos/butterfly effect, trace a second nearby trajectory (e.g. x+0.0001 in RED) to show divergence!\n"
    "5. Implement Plan.teaching_script narration lines verbatim in sequential order.\n"
    "6. Silent self.play(...) without a voiceover block will fail static validation.\n"
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
                for b in (script.get("beats") or [])[:16]
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

    # Synthesize fallback teaching beats so local coder always has voiceovers
    topic_name = str(compact.get("topic") or "this topic")
    compact["teaching_script"] = {
        "scene_class_name": str((compact.get("class_names") or ["MainScene"])[0]),
        "throughline": f"Visual exploration of {topic_name}.",
        "beats": [
            {"id": "b1", "visual": "Title and core concept", "narration": f"In this lesson, we explore the foundations of {topic_name}."},
            {"id": "b2", "visual": "Setup components and frame", "narration": f"We begin by establishing the essential framework of {topic_name}."},
            {"id": "b3", "visual": "Key mathematical relationship", "narration": "Notice how this fundamental formula connects the components together."},
            {"id": "b4", "visual": "Visual transformation and insight", "narration": "Observing this transformation gives clear geometric intuition."},
            {"id": "b5", "visual": "Summary and conclusion", "narration": f"This completes our visual walkthrough of {topic_name}."},
        ],
    }
    return compact


LOCAL_CODER_CODEMODE_HINT = (
    "Call tools ONLY via run_code (CodeMode): wrap Manim source in triple-quoted "
    "strings and await manim_write / compile_manim_code. "
    "Never put from manim import * at the top level of run_code. "
    "Never put await manim_write inside the code string itself. "
    "Do not use input() as this runs headlessly.\n"
)


def build_coder_user_prompt(
    *,
    topic: str,
    subject: str,
    output_dir: Any,
    plan_payload: dict[str, Any],
    compact: bool = False,
    include_codemode_hint: bool = False,
    length: str | None = None,
) -> str:
    payload = dict(plan_payload)
    # Annotate teaching_script beats with cinematic hint tags before compacting.
    script = payload.get("teaching_script")
    if isinstance(script, dict):
        payload["teaching_script"] = annotate_teaching_script(
            script, topic=topic, subject=str(subject)
        )
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
    if length:
        bits.append(
            f"Target Video Length: {length} (Pace animations and voiceovers calmly, with natural pauses and full explanations to fill this educational duration with deep clarity)."
        )
    if include_codemode_hint:
        bits.append(LOCAL_CODER_CODEMODE_HINT.rstrip("\n"))
    bits.append(CODER_SCRIPT_HINT.rstrip("\n"))
    bits.append(CINEMATIC_HINT_LEGEND.rstrip("\n"))
    template_boilerplate = get_template_for_duration(length or "medium")
    bits.append(
        f"RECOMMENDED PRODUCTION TEMPLATE (Strictly adhere to this architecture):\n```python\n{template_boilerplate}\n```"
    )
    bits.append(f"Plan:\n{plan_text}")
    return "\n".join(bits) + "\n"



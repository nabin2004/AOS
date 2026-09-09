"""
cinematic_hints.py — Pedagogical Cinematic Hinting System
==========================================================

Injects *structured cinematic hint tags* directly into each teaching beat's
``visual`` description **before** the prompt is sent to the Manim coder.

Design principle
----------------
We never force schema fields (that breaks structured-output with small models).
Instead we *annotate the natural-language plan* with concise hint tokens that
a capable LLM reads and acts on — exactly like inline stage-directions in a
screenplay.

Example output for a single beat::

    "visual": "[CAMERA_ORBIT] [UPDATER: rotating dot] Lorenz attractor in 3D; two trajectories diverging."

Token catalogue
---------------
[CAMERA_ORBIT]       — ThreeDScene: begin_ambient_camera_rotation + phi/theta sweep
[CAMERA_ZOOM_IN]     — MovingCameraScene: zoom frame to focal element
[CAMERA_ZOOM_OUT]    — Pull back to show the full picture
[CAMERA_PAN]         — Pan the camera frame to follow motion
[UPDATER: <desc>]    — ValueTracker + add_updater lambda animating <desc>
[BACKGROUND: <clr>]  — self.camera.background_color = <clr>
[PARTICLE_FIELD]     — Animated field of dots/particles
[TRACE_PATH]         — TracedPath to show trajectory over time
[MORPH_EQUATION]     — TransformMatchingTex / ReplacementTransform algebra morph
[HIGHLIGHT_PULSE]    — Indicate + Flash on key symbol
[SLOW_REVEAL]        — LaggedStart(FadeIn, lag_ratio=0.2) element by element
[SPLIT_SCREEN]       — Two VGroups side-by-side for comparison

Usage::

    from cinematic_hints import annotate_teaching_script, CINEMATIC_HINT_LEGEND

    script_payload = annotate_teaching_script(script_payload, topic=topic, subject=subject)
    # CINEMATIC_HINT_LEGEND is appended to the coder user prompt so the model
    # knows exactly which Manim pattern each tag maps to.
"""

from __future__ import annotations

import copy
import re
from typing import Any

# ---------------------------------------------------------------------------
# Keyword tables for heuristic matching
# ---------------------------------------------------------------------------

_3D_KEYWORDS = {
    "3d", "three-d", "3-d", "surface", "lorenz", "attractor", "trajectory",
    "spiral", "helix", "torus", "sphere", "manifold", "orbit", "orbital",
    "space curve", "parametric", "rotating", "rotation axis", "curl",
    "divergence", "field line", "magnetic", "electromagnetic", "wave packet",
    "phase space", "strange attractor", "vector field 3d",
}

_ORBIT_KEYWORDS = {
    "orbit", "rotate camera", "revolve", "view angle", "perspective",
    "three-dimensional", "3-dimensional", "look around", "fly around",
    "ambient rotation",
}

_ZOOM_KEYWORDS = {
    "zoom in", "focus on", "close-up", "magnify", "detail",
    "enlarge", "center on", "emphasize",
}

_ZOOM_OUT_KEYWORDS = {
    "zoom out", "pull back", "reveal whole", "full picture", "overview",
    "step back", "show all",
}

_PAN_KEYWORDS = {
    "pan", "scroll", "move across", "slide to", "follow the",
    "track the point", "sweep",
}

_UPDATER_KEYWORDS = {
    "continuously", "real-time", "as theta changes", "as t increases",
    "as x varies", "dynamic", "live update", "track", "trace", "animate over",
    "moving dot", "moving point", "evolving", "oscillat", "pulsing",
    "value tracker", "watch",
}

_BACKGROUND_DARK_KEYWORDS = {
    "night", "cosmos", "space", "universe", "dark", "stellar", "galaxy",
    "black hole",
}

_BACKGROUND_PHYSICS_KEYWORDS = {
    "wave", "quantum", "field", "energy", "electric", "magnetic", "photon",
    "electron", "proton",
}

_PARTICLE_KEYWORDS = {
    "field", "particles", "wave front", "ripple", "propagation",
    "radiation", "lattice", "distribution", "scatter",
}

_TRACE_KEYWORDS = {
    "trace", "path", "trajectory", "route", "follows", "leaves a trail",
    "leaves trail", "arc", "orbit path", "curve traces",
}

_MORPH_KEYWORDS = {
    "transform", "derive", "derivation", "step by step", "step-by-step",
    "algebra", "rearrange", "substitute", "factor", "simplify",
    "rewrite", "expand", "cancel", "becomes",
}

_HIGHLIGHT_KEYWORDS = {
    "key term", "important", "notice", "pay attention", "crucial",
    "observe that", "highlight", "mark", "point out",
}

_SLOW_REVEAL_KEYWORDS = {
    "reveal", "appear one by one", "appear in sequence", "build up",
    "step-by-step appear", "element by element", "list", "bullet",
}

_SPLIT_KEYWORDS = {
    "compare", "comparison", "side by side", "before and after",
    "two cases", "contrast", "left vs right",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _text(beat: dict[str, Any]) -> str:
    """Combine visual + narration + takeaway into one lowercase search string."""
    parts = [
        str(beat.get("visual", "")),
        str(beat.get("narration", "")),
        str(beat.get("takeaway", "")),
    ]
    return " ".join(parts).lower()


def _matches(text: str, keywords: set[str]) -> bool:
    return any(kw in text for kw in keywords)


def _subject_is_3d(subject: str, topic: str) -> bool:
    combined = (subject + " " + topic).lower()
    return _matches(combined, _3D_KEYWORDS)


def _short_visual(visual: str, max_words: int = 6) -> str:
    """Distil a visual description to a compact tag-friendly phrase."""
    words = re.sub(r"[^\w\s]", "", visual).split()
    return " ".join(words[:max_words]) if words else "key element"


# ---------------------------------------------------------------------------
# Per-beat hint annotation
# ---------------------------------------------------------------------------

def _hints_for_beat(
    beat: dict[str, Any],
    beat_index: int,
    total_beats: int,
    topic: str,
    subject: str,
    is_3d_topic: bool,
) -> list[str]:
    """Return a list of hint tags to prepend to this beat's visual."""
    hints: list[str] = []
    t = _text(beat)
    visual = str(beat.get("visual", "")).lower()

    # Camera: orbit (3D rotation) ---------------------------------------------
    if is_3d_topic or _matches(t, _ORBIT_KEYWORDS | _3D_KEYWORDS):
        # Establish orbit on first/introductory 3D beats
        if beat_index <= 1 or "introduce" in visual or visual.startswith("show"):
            hints.append("[CAMERA_ORBIT]")

    # Camera: zoom in to focal element ----------------------------------------
    if _matches(t, _ZOOM_KEYWORDS):
        hints.append("[CAMERA_ZOOM_IN]")

    # Camera: zoom out / overview ---------------------------------------------
    if _matches(t, _ZOOM_OUT_KEYWORDS) or (
        beat_index == total_beats - 1 and is_3d_topic
    ):
        hints.append("[CAMERA_ZOOM_OUT]")

    # Camera: pan/follow -------------------------------------------------------
    if _matches(t, _PAN_KEYWORDS):
        hints.append("[CAMERA_PAN]")

    # Updater: dynamic/continuous animation ------------------------------------
    if _matches(t, _UPDATER_KEYWORDS):
        updater_what = _short_visual(str(beat.get("visual", "")), max_words=6)
        hints.append(f"[UPDATER: {updater_what}]")

    # Background colour --------------------------------------------------------
    if beat_index == 0:
        if _matches(t, _BACKGROUND_DARK_KEYWORDS):
            hints.append("[BACKGROUND: #0d1117]")
        elif _matches(t, _BACKGROUND_PHYSICS_KEYWORDS):
            hints.append("[BACKGROUND: #0a0a1e]")

    # Particle field -----------------------------------------------------------
    if _matches(t, _PARTICLE_KEYWORDS):
        hints.append("[PARTICLE_FIELD]")

    # Traced path --------------------------------------------------------------
    if _matches(t, _TRACE_KEYWORDS):
        hints.append("[TRACE_PATH]")

    # Step-by-step equation morphing ------------------------------------------
    if _matches(t, _MORPH_KEYWORDS):
        hints.append("[MORPH_EQUATION]")

    # Highlight pulse on key term ---------------------------------------------
    if _matches(t, _HIGHLIGHT_KEYWORDS):
        hints.append("[HIGHLIGHT_PULSE]")

    # Slow sequential reveal --------------------------------------------------
    if _matches(t, _SLOW_REVEAL_KEYWORDS):
        hints.append("[SLOW_REVEAL]")

    # Split-screen comparison -------------------------------------------------
    if _matches(t, _SPLIT_KEYWORDS):
        hints.append("[SPLIT_SCREEN]")

    # Heuristic: last beat always gets a calm zoom-out overview ---------------
    if beat_index == total_beats - 1 and "[CAMERA_ZOOM_OUT]" not in hints:
        hints.append("[CAMERA_ZOOM_OUT]")

    return hints


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def annotate_beats(
    beats: list[dict[str, Any]],
    topic: str = "",
    subject: str = "",
) -> list[dict[str, Any]]:
    """
    Return a NEW list of beat dicts with cinematic hint tags prepended to each
    beat's ``visual`` field.

    Parameters
    ----------
    beats:
        Raw beat dicts (from ``TeachingScript.beats`` after ``.model_dump()``).
    topic:
        Topic string (used for 3D detection and background selection).
    subject:
        Subject string (e.g. ``"physics"``, ``"math"``).

    Returns
    -------
    Annotated copies — originals are untouched.
    """
    if not beats:
        return beats

    is_3d = _subject_is_3d(subject, topic)
    total = len(beats)
    out: list[dict[str, Any]] = []

    for i, beat in enumerate(beats):
        beat_copy = copy.deepcopy(beat)
        tags = _hints_for_beat(
            beat_copy,
            beat_index=i,
            total_beats=total,
            topic=topic,
            subject=subject,
            is_3d_topic=is_3d,
        )
        if tags:
            prefix = " ".join(tags) + " "
            beat_copy["visual"] = prefix + str(beat_copy.get("visual", ""))
        out.append(beat_copy)

    return out


def annotate_teaching_script(
    script_payload: dict[str, Any],
    topic: str = "",
    subject: str = "",
) -> dict[str, Any]:
    """
    Annotate the ``beats`` list inside a full teaching-script payload dict.

    Returns a *new* dict — originals are untouched.
    """
    if not isinstance(script_payload, dict):
        return script_payload

    beats = script_payload.get("beats")
    if not isinstance(beats, list):
        return script_payload

    annotated = annotate_beats(beats, topic=topic, subject=subject)
    result = dict(script_payload)
    result["beats"] = annotated
    return result


# ---------------------------------------------------------------------------
# Cinematic instructions injected into the coder user prompt
# ---------------------------------------------------------------------------

CINEMATIC_HINT_LEGEND = """\
CINEMATIC HINT TAGS (inline stage-directions — implement each tag in Manim):
  [CAMERA_ORBIT]        -> ThreeDScene.begin_ambient_camera_rotation(rate=0.15) after first object
                           appears; set_camera_orientation(phi=70*DEGREES, theta=-60*DEGREES).
  [CAMERA_ZOOM_IN]      -> MovingCameraScene: self.play(self.camera.frame.animate.scale(0.55).move_to(focal))
  [CAMERA_ZOOM_OUT]     -> self.play(self.camera.frame.animate.scale(2.0).move_to(ORIGIN))
  [CAMERA_PAN]          -> self.play(self.camera.frame.animate.shift(direction * units))
  [UPDATER: <desc>]     -> tracker = ValueTracker(start)
                           obj.add_updater(lambda m: m.move_to/set_value(...tracker.get_value()...))
                           self.play(tracker.animate.set_value(end), run_time=duration)
                           obj.remove_updater(...)  # after the beat
  [BACKGROUND: <color>] -> self.camera.background_color = <color>  (set at top of construct)
  [PARTICLE_FIELD]      -> dots = VGroup(*[Dot(point=[np.random.uniform(-5,5), np.random.uniform(-3,3), 0], radius=0.04)
                               for _ in range(40)]); self.play(LaggedStart(*[FadeIn(d) for d in dots], lag_ratio=0.02))
  [TRACE_PATH]          -> trace = TracedPath(moving_dot.get_center, dissipating_time=2.0, stroke_color=BLUE)
                           self.add(trace); self.play(MoveAlongPath(moving_dot, path, run_time=...))
  [MORPH_EQUATION]      -> Use TransformMatchingTex(eq_old, eq_new) or ReplacementTransform;
                           self.wait(1.5) between morphs so learner can read each step.
  [HIGHLIGHT_PULSE]     -> self.play(Indicate(target, color=YELLOW, scale_factor=1.3))
                           self.play(Flash(target, color=YELLOW, flash_radius=0.4))
  [SLOW_REVEAL]         -> self.play(LaggedStart(*[FadeIn(m, shift=UP*0.2) for m in group], lag_ratio=0.18))
  [SPLIT_SCREEN]        -> left_grp = VGroup(...).to_edge(LEFT, buff=0.5)
                           right_grp = VGroup(...).to_edge(RIGHT, buff=0.5)
                           self.play(FadeIn(left_grp), FadeIn(right_grp))

CRITICAL: All Manim positions and points MUST be 3D coordinates (e.g. [x, y, 0] or np.random.uniform(-3, 3, 3)). Never pass 2D arrays to Dot(point=...), Line, or Arrow.
"""

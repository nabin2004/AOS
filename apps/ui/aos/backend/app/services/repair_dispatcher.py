"""Repair Dispatcher: Translates human visual critiques into structured agent repair directives."""

from __future__ import annotations

from app.schemas.critique import CritiqueCategory, CritiqueSubmissionRequest

REPAIR_STRATEGIES: dict[CritiqueCategory, dict[str, str]] = {
    CritiqueCategory.POSITIONING: {
        "focus": "Spatial layout, bounding boxes, and collision avoidance",
        "guidance": (
            "CRITICAL POSITIONING DIRECTIVES:\n"
            "1. Inspect all `.next_to()`, `.shift()`, `.to_edge()`, and `.move_to()` coordinate calls.\n"
            "2. Ensure all text and MathTex equations have at least 0.4 units of buffer margin from screen edges and diagrams.\n"
            "3. If equations or labels overlap with trajectories, group related mobjects with `VGroup` and arrange them vertically or horizontally with `buff=0.5`.\n"
            "4. Never place a formula directly over an active trajectory or animated graph."
        ),
    },
    CritiqueCategory.VISUAL_DRIFT: {
        "focus": "Trajectory divergence, coordinate frame drift, and camera continuity",
        "guidance": (
            "CRITICAL VISUAL DRIFT DIRECTIVES:\n"
            "1. The visual animation deviates over time from the planned scene progression.\n"
            "2. Reset any drifting coordinate frame or camera angle back to the stable canonical perspective (`self.camera.frame.animate.reorient(...)` or default frame).\n"
            "3. Ensure mobjects introduced in earlier beats remain anchored or are cleanly faded out (`FadeOut`) before new elements occupy that coordinate space.\n"
            "4. Verify that parameters modulating geometry (e.g. sigma, rho, beta in Lorenz, or frequency in Fourier) do not send coordinates off-screen."
        ),
    },
    CritiqueCategory.VISIBILITY: {
        "focus": "Scale, line stroke thickness, font size, and contrast",
        "guidance": (
            "CRITICAL VISIBILITY & SCALE DIRECTIVES:\n"
            "1. The user noted elements are too small, difficult to read, or visually obscured.\n"
            "2. Increase the scale of primary curves and trajectories using `.scale(1.25)` or `.scale(1.4)`.\n"
            "3. Increase stroke width of curves and plots to at least `stroke_width=4.0` (avoid hairline strokes).\n"
            "4. Increase LaTeX font size with `font_size=38` or `font_size=42`.\n"
            "5. Ensure high-contrast colors (e.g. `YELLOW`, `TEAL`, `BLUE_C`, `RED_C`) against dark background."
        ),
    },
    CritiqueCategory.TIMING: {
        "focus": "Animation beat durations, run_time, and pacing synchronization",
        "guidance": (
            "CRITICAL TIMING & SYNC DIRECTIVES:\n"
            "1. Visual beats are moving too fast or out of sync with the conceptual pace.\n"
            "2. Increase animation durations: change `run_time=1.0` to `run_time=2.5` or `run_time=3.0` for intricate geometric constructs.\n"
            "3. Insert deliberate pauses (`self.wait(1.5)`) after revealing critical equations or milestone trajectory points so the viewer can absorb the insight.\n"
            "4. Use smoother rate functions such as `rate_func=smooth` or `rate_func=linear` where appropriate."
        ),
    },
    CritiqueCategory.SCIENTIFIC_ACCURACY: {
        "focus": "Mathematical equations, physical formulas, parameter fidelity, and numerical consistency",
        "guidance": (
            "CRITICAL SCIENTIFIC ACCURACY DIRECTIVES:\n"
            "1. The user identified a conceptual, mathematical, or scientific error.\n"
            "2. Re-verify the core formulas in `MathTex` against standard mathematical/scientific definitions.\n"
            "3. If numerical integration or simulation is used (e.g. SciPy `solve_ivp`), verify the initial conditions and differential equation system.\n"
            "4. Correct any incorrect signs, exponents, constants, or units in the visual representation."
        ),
    },
    CritiqueCategory.EXPLANATION: {
        "focus": "Pedagogical sequencing, visual proofs, and concept progression",
        "guidance": (
            "CRITICAL PEDAGOGICAL CLARITY DIRECTIVES:\n"
            "1. The concept is technically present but visually confusing or poorly explained.\n"
            "2. Add visual arrows (`Arrow`), highlight boxes (`SurroundingRectangle`), or callout labels directing attention to key phenomena.\n"
            "3. Introduce concepts progressively (step-by-step building) rather than displaying complex diagrams all at once.\n"
            "4. Connect equations directly to the geometric motion with matching color coding."
        ),
    },
    CritiqueCategory.NARRATION: {
        "focus": "Spoken commentary, technical terms, and verbal clarity",
        "guidance": (
            "CRITICAL NARRATION DIRECTIVES:\n"
            "1. The voiceover script requires revision for clarity, tone, or accuracy.\n"
            "2. Use precise scientific terminology while maintaining engaging pedagogical intuition.\n"
            "3. Align verbal descriptions with exact moments of visual emphasis."
        ),
    },
    CritiqueCategory.GENERAL: {
        "focus": "Overall polish and user-directed adjustments",
        "guidance": (
            "CRITICAL REPAIR DIRECTIVES:\n"
            "1. Carefully address the user's specific feedback.\n"
            "2. Preserve the parts of the animation that worked well while repairing the targeted issue."
        ),
    },
}


def build_repair_prompt(request: CritiqueSubmissionRequest) -> str:
    """Generate a high-precision repair prompt for the Manim coder agent."""
    strategy = REPAIR_STRATEGIES.get(request.category, REPAIR_STRATEGIES[CritiqueCategory.GENERAL])

    ts_str = f" at {request.timestamp_seconds:.1f}s" if request.timestamp_seconds is not None else ""
    target_str = f" for element '{request.target_object}'" if request.target_object else ""

    parts = [
        f"HUMAN VISUAL CRITIQUE (Revision {request.revision}):",
        f"- Failure Category: {request.category.value.upper()}",
        f"- Specific Observation{ts_str}{target_str}: {request.feedback}",
        f"- Severity: {request.severity.value.upper()}",
        "",
        "TARGETED REPAIR STRATEGY:",
        strategy["guidance"],
        "",
        "INSTRUCTIONS FOR REPAIR AGENT:",
        "1. Modify the Manim source code to fix this specific issue without breaking unaffected scenes.",
        "2. Ensure all mobjects remain within frame boundaries and render cleanly in 1080p.",
        "3. Output the complete, corrected, executable Manim script.",
    ]

    return "\n".join(parts)

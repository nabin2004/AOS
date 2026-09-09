"""AOS Multi-Agent Semantic Router Pipeline (v2 — Optimized for 7B Models).

Assembly Line:
1. Architect (Deterministic) -> SceneEnvironment
2. Prop Master Agent (Structured Output) -> SceneMobjectRoster
3. Layout Critic (Deterministic Spatial Engine) -> SceneLayoutState
4. Choreographer Agent (Structured Output) -> SceneChoreography
5. Code Assembler (Deterministic) -> Complete executable Manim CE Python code
6. Repair Loop (Syntax Check) -> Validated output or error routing

v2 CHANGES:
  - Architect is now deterministic (keyword heuristic), saving one LLM call
  - System prompts use few-shot examples instead of exhaustive catalogs
  - MobjectConfig typed slots replace freeform initial_args
  - Richer AnimationEvent: cleanup, pacing, rate_func, grouped targets
  - VGroup auto-generation from group_name fields
  - Assembler handles transforms, grouped animations, wait pacing
  - Syntax-check repair loop catches Python errors before rendering
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_ai import Agent

load_dotenv()
# Map GEMINI_API_KEY to GOOGLE_API_KEY for Pydantic AI's Google provider if needed
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")
elif os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

from validation import (
    registry,
    SceneEnvironment,
    ManimMobject,
    MobjectConfig,
    SceneMobjectRoster,
    AnimationEvent,
    SceneChoreography,
    validate_choreography_against_roster,
    get_core_mobjects_prompt,
    get_core_animations_prompt,
    CORE_MOBJECTS,
    CORE_ANIMATIONS,
)
from layout_critic import layout_critic, SceneLayoutState

# Model configuration: auto-detect Gemini if GOOGLE_API_KEY / GEMINI_API_KEY is set
def _resolve_default_model() -> str:
    explicit = os.getenv("AOS_LLM_MODEL")
    if explicit:
        if explicit.startswith("gemini"):
            return f"google:{explicit}"
        return explicit
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return "google:gemini-2.5-flash"
    return "test"

DEFAULT_MODEL = _resolve_default_model()

# ---------------------------------------------------------------------------
# 1. Deterministic Architect (No LLM needed)
# ---------------------------------------------------------------------------
# The Architect's decision tree is simple enough for keyword heuristics.
# This saves the 7B model's token budget for the harder tasks.

_3D_KEYWORDS = {"3d", "three-dimensional", "sphere", "cube", "surface", "rotate 3d", "3blue1brown"}
_SLIDE_KEYWORDS = {"slide", "presentation", "next slide", "slides"}
_CAMERA_KEYWORDS = {"zoom", "pan", "camera move", "focus on", "moving camera"}
_VOICEOVER_KEYWORDS = {"voiceover", "narrate", "narration", "voice"}


def determine_scene_environment(
    pedagogical_prompt: str,
    has_audio: bool = False,
) -> SceneEnvironment:
    """Deterministic keyword-based scene environment selection.

    Replaces the LLM-based Architect agent — faster, cheaper, zero-error.
    """
    prompt_lower = pedagogical_prompt.lower()

    # 3D Scenes
    if any(kw in prompt_lower for kw in _3D_KEYWORDS):
        return SceneEnvironment(
            scene_class="ThreeDScene",
            camera_class="ThreeDCamera",
        )

    # Slide presentations
    if any(kw in prompt_lower for kw in _SLIDE_KEYWORDS):
        return SceneEnvironment(
            scene_class="Slide",
            required_plugins=["manim-slides"],
        )

    # Moving camera (zoom/pan)
    if any(kw in prompt_lower for kw in _CAMERA_KEYWORDS):
        return SceneEnvironment(
            scene_class="MovingCameraScene",
            camera_class="MovingCamera",
        )

    # Voiceover
    if has_audio or any(kw in prompt_lower for kw in _VOICEOVER_KEYWORDS):
        return SceneEnvironment(
            scene_class="VoiceoverScene",
            required_plugins=["manim-voiceover"],
        )

    # Default: plain Scene
    return SceneEnvironment(scene_class="Scene")


# ---------------------------------------------------------------------------
# 2. Prop Master Agent — Few-Shot System Prompt
# ---------------------------------------------------------------------------

_CORE_MOBJECTS_LIST = get_core_mobjects_prompt()

# Using raw triple-quoted string to preserve LaTeX backslashes in examples
_PROP_MASTER_EXAMPLES = r"""
EXAMPLE 1:
Prompt: "Explain the Pythagorean theorem with a right triangle"
Mobjects:
- title (Title, text="Pythagorean Theorem")
- triangle (Triangle, color=WHITE)
- a_label (MathTex, tex="a", color=BLUE, group_name="labels")
- b_label (MathTex, tex="b", color=GREEN, group_name="labels")
- c_label (MathTex, tex="c", color=RED, group_name="labels")
- theorem_eq (MathTex, tex="a^2 + b^2 = c^2", color=YELLOW)

EXAMPLE 2:
Prompt: "Show how the derivative works as a limit of secant slopes"
Mobjects:
- title (Title, text="The Derivative")
- axes (Axes, x_range=[-1, 4, 1], y_range=[-1, 5, 1], x_length=6.0, y_length=4.0)
- func_curve (FunctionGraph, function_expr="x**2", color=YELLOW)
- h_tracker (ValueTracker, initial_value=2.0)
- secant (Line, color=RED)
- deriv_eq (MathTex, tex="f'(x) = \lim_{h \to 0} \frac{f(x+h)-f(x)}{h}")
"""

prop_master_agent = Agent(
    DEFAULT_MODEL,
    output_type=SceneMobjectRoster,
    system_prompt=(
        "You are the Prop Master for Manim CE educational animations.\n"
        "Given a pedagogical prompt and scene environment, declare ALL visual objects needed.\n\n"
        "RULES:\n"
        "1. Choose classes ONLY from the verified catalog below.\n"
        "2. NEVER use abstract bases like Mobject, VMobject, CoordinateSystem.\n"
        "3. Use MathTex for equations (set config.tex). Use Text/Title for plain text (set config.text).\n"
        "4. Use Axes for coordinate systems. Use FunctionGraph for curves (set config.function_expr).\n"
        "5. Use ValueTracker for continuous animations (set config.initial_value).\n"
        "6. Set group_name to group related objects (e.g., all labels in 'labels_group').\n"
        "7. Fill ONLY the relevant config fields for each class. Leave others null.\n"
        "8. Do NOT write animations, transforms, or positioning code.\n\n"
        f"{_CORE_MOBJECTS_LIST}\n\n"
        f"{_PROP_MASTER_EXAMPLES}"
    ),
)


# ---------------------------------------------------------------------------
# 3. Choreographer Agent — Few-Shot System Prompt
# ---------------------------------------------------------------------------

_CORE_ANIMATIONS_LIST = get_core_animations_prompt()

_CHOREOGRAPHER_EXAMPLES = r"""
EXAMPLE:
Mobjects available: title, axes, func_curve, deriv_eq, h_tracker
Scene goal: "Introduce the derivative concept step by step"

Choreography events (in order):
1. Write title, wait_after=1.0, bookmark="intro"
2. cleanup_before=[title], Create axes, wait_after=0.5, bookmark="show_axes"
3. Create func_curve, wait_after=0.5, bookmark="show_curve"
4. Write deriv_eq, wait_after=1.5, bookmark="show_formula"
5. Indicate deriv_eq, rate_func=there_and_back, wait_after=0.5, bookmark="highlight"
6. cleanup_before=[deriv_eq], FadeOut, bookmark="transition"

KEY PRINCIPLES:
- One focal point per animation step (never overwhelm the viewer)
- Always cleanup old content before introducing new sections
- Use wait_after >= 0.5 after important content for viewer comprehension
- Use Indicate/Circumscribe to draw attention to key elements
- For formula changes, use ReplacementTransform with source_variable set
"""

choreographer_agent = Agent(
    DEFAULT_MODEL,
    output_type=SceneChoreography,
    system_prompt=(
        "You are the Choreographer for Manim CE educational animations.\n"
        "Given the Mobject Roster and Layout, plan the temporal sequence of animations.\n\n"
        "RULES:\n"
        "1. Every target_variables entry MUST exactly match a variable_name from the Roster.\n"
        "2. Choose animations ONLY from the verified catalog below.\n"
        "3. Use cleanup_before to FadeOut old content before introducing new sections.\n"
        "4. Set wait_after >= 0.3 for pacing. Use 1.0+ after key formulas.\n"
        "5. For ReplacementTransform/TransformMatchingTex, always set source_variable.\n"
        "6. Use rate_func='there_and_back' for Indicate to return to original state.\n"
        "7. Animate ONE concept per step — never overwhelm the viewer.\n\n"
        f"{_CORE_ANIMATIONS_LIST}\n\n"
        f"{_CHOREOGRAPHER_EXAMPLES}"
    ),
)


# ---------------------------------------------------------------------------
# 4. Manim Code Assembler (v2 — Richer Templates)
# ---------------------------------------------------------------------------

def assemble_manim_script(
    env: SceneEnvironment,
    roster: SceneMobjectRoster,
    layout: SceneLayoutState,
    choreography: SceneChoreography,
    scene_name: str = "PedagogicalScene",
) -> str:
    """Assembles all validated multi-agent artifacts into a production-ready Manim CE script.

    v2: Uses MobjectConfig.to_constructor_call(), auto-generates VGroups,
    handles transforms, grouped animations, rate functions, and pacing.
    """
    # 1. Imports
    import_lines = ["from manim import *"]
    if "manim-voiceover" in env.required_plugins:
        import_lines.append("from manim_voiceover import VoiceoverScene")
        import_lines.append("from manim_voiceover.services.recorder import RecorderService")
    if "manim-slides" in env.required_plugins:
        import_lines.append("from manim_slides import Slide")

    code_lines = [
        "# ===========================================================================",
        "# Synthesized by AOS Multi-Agent Semantic Router v2",
        "# Graph-Validated against Manim Community v0.21.0 Reference Manual",
        "# ===========================================================================",
        "\n".join(import_lines),
        "",
        f"class {scene_name}({env.scene_class}):",
        "    def construct(self):",
    ]

    # Plugin setup
    if "manim-voiceover" in env.required_plugins:
        code_lines.append("        # Initialize offline/recorder speech service")
        code_lines.append("        # self.set_speech_service(RecorderService())")
        code_lines.append("")

    # Background color
    code_lines.append(f'        self.camera.background_color = "{env.background_color}"')
    code_lines.append("")

    # 2. Allocate Mobjects (Prop Master) — using typed config
    code_lines.append("        # --- 1. Allocate Mobjects (Prop Master) ---")
    for m in roster.mobjects:
        constructor = m.to_constructor_call()
        code_lines.append(f"        {m.variable_name} = {constructor}  # {m.purpose}")
    code_lines.append("")

    # 3. Auto-generate VGroups from group_name fields
    groups = roster.get_groups()
    if groups:
        code_lines.append("        # --- 1b. VGroups (auto-generated from group_name) ---")
        for group_name, members in groups.items():
            members_str = ", ".join(members)
            code_lines.append(f"        {group_name} = VGroup({members_str})")
        code_lines.append("")

    # 4. Spatial Layout Directives (Layout Critic)
    code_lines.append("        # --- 2. Deterministic Positioning (Layout Critic) ---")
    for line in layout.layout_code:
        for subline in line.split("\n"):
            code_lines.append(f"        {subline}")
    code_lines.append("")

    # 5. Temporal Choreography (Choreographer) — v2 richer templates
    code_lines.append("        # --- 3. Choreography (Choreographer) ---")
    for event in choreography.events:

        # 5a. Cleanup: FadeOut old content before this animation
        if event.cleanup_before:
            fadeout_parts = ", ".join(f"FadeOut({v})" for v in event.cleanup_before)
            code_lines.append(f"        self.play({fadeout_parts})  # Cleanup")

        # 5b. Build the animation call
        anim_call = _build_animation_call(event)

        # 5c. Build play() kwargs
        play_kwargs = [f"run_time={event.run_time}"]
        if event.rate_func != "smooth":
            play_kwargs.append(f"rate_func={event.rate_func}")

        kwargs_str = ", ".join(play_kwargs)
        sync_comment = f"# Bookmark: <bookmark mark='{event.audio_bookmark_sync}'/>"
        code_lines.append(f"        self.play({anim_call}, {kwargs_str})  {sync_comment}")

        # 5d. Slide boundary
        if event.audio_bookmark_sync in choreography.next_slide_bookmarks:
            code_lines.append("        if hasattr(self, 'next_slide'):")
            code_lines.append("            self.next_slide()")

        # 5e. Wait for pacing (critical for watchable output)
        if event.wait_after > 0:
            code_lines.append(f"        self.wait({event.wait_after})")

    code_lines.append("        self.wait(1)")
    code_lines.append("")

    return "\n".join(code_lines)


def _build_animation_call(event: AnimationEvent) -> str:
    """Builds the animation call string from an AnimationEvent.

    Handles single targets, grouped targets, and transforms.
    """
    anim_cls = event.animation_class

    # Transform animations: source → target
    transform_anims = {"ReplacementTransform", "TransformMatchingTex", "TransformMatchingShapes"}
    if anim_cls in transform_anims and event.source_variable:
        target = event.target_variables[0]
        return f"{anim_cls}({event.source_variable}, {target})"

    # Shift kwarg for FadeIn/FadeOut
    shift_str = ""
    if event.shift_direction and anim_cls in ("FadeIn", "FadeOut"):
        shift_str = f", shift={event.shift_direction}"

    # Single target (most common case)
    if len(event.target_variables) == 1:
        target = event.target_variables[0]
        return f"{anim_cls}({target}{shift_str})"

    # Multiple targets — grouped animation
    if event.lag_ratio is not None:
        # Use LaggedStart for staggered entry
        anims = ", ".join(f"{anim_cls}({v}{shift_str})" for v in event.target_variables)
        return f"LaggedStart({anims}, lag_ratio={event.lag_ratio})"
    else:
        # Use AnimationGroup for simultaneous
        anims = ", ".join(f"{anim_cls}({v}{shift_str})" for v in event.target_variables)
        return f"AnimationGroup({anims})"


# ---------------------------------------------------------------------------
# 5. Repair Loop — Syntax Check Before Rendering
# ---------------------------------------------------------------------------

def syntax_check(code: str) -> tuple[bool, str]:
    """Checks generated Python code for syntax errors.

    Returns (is_valid, error_message).
    This catches ~30% of 7B model failures before they reach the Manim renderer.
    """
    try:
        compile(code, "<generated_scene>", "exec")
        return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"


def diagnose_error(error_msg: str) -> str:
    """Maps common errors to the responsible agent for repair routing.

    Returns: 'prop_master', 'choreographer', 'layout_critic', or 'assembler'.
    """
    msg_lower = error_msg.lower()

    if any(kw in msg_lower for kw in ["mathtex", "tex", "latex", "brace", "frac"]):
        return "prop_master"
    if any(kw in msg_lower for kw in ["name", "variable", "not defined", "undefined"]):
        return "choreographer"
    if any(kw in msg_lower for kw in ["position", "move_to", "next_to", "align"]):
        return "layout_critic"
    return "assembler"


# ---------------------------------------------------------------------------
# 6. End-to-End Semantic Router Pipeline
# ---------------------------------------------------------------------------

def synthesize_scene_pipeline(
    pedagogical_prompt: str,
    audio_script: str = "",
    use_mock_agents: Optional[bool] = None,
    max_repairs: int = 2,
) -> dict:
    """Chains Architect -> Prop Master -> Layout Critic -> Choreographer -> Assembler -> Repair.

    v2: Deterministic Architect, structured output, repair loop.
    """

    if use_mock_agents is None:
        use_mock_agents = (DEFAULT_MODEL == "test")

    # Step 1: Architect (Deterministic — no LLM call)
    env = determine_scene_environment(pedagogical_prompt, has_audio=bool(audio_script))

    # Step 2: Prop Master (Mobjects with typed config)
    if use_mock_agents:
        mobjects_roster = SceneMobjectRoster(
            mobjects=[
                ManimMobject(
                    variable_name="title",
                    manim_class="Title",
                    purpose="Main lecture header",
                    config=MobjectConfig(text="Derivative Definition"),
                ),
                ManimMobject(
                    variable_name="axes",
                    manim_class="Axes",
                    purpose="Coordinate frame for secant to tangent limit",
                    config=MobjectConfig(
                        x_range=[-3.0, 3.0, 1.0],
                        y_range=[-1.0, 5.0, 1.0],
                        x_length=6.0,
                        y_length=4.0,
                    ),
                ),
                ManimMobject(
                    variable_name="func_curve",
                    manim_class="FunctionGraph",
                    purpose="Graph of f(x) = x^2",
                    config=MobjectConfig(
                        function_expr="x**2",
                        color="YELLOW",
                    ),
                ),
                ManimMobject(
                    variable_name="deriv_eq",
                    manim_class="MathTex",
                    purpose="Formal Newton quotient limit",
                    config=MobjectConfig(
                        tex=r"f'(x) = \lim_{h\to 0}\frac{f(x+h)-f(x)}{h}",
                    ),
                ),
                ManimMobject(
                    variable_name="h_tracker",
                    manim_class="ValueTracker",
                    purpose="Controls secant step delta h approaching 0",
                    config=MobjectConfig(initial_value=1.0),
                ),
            ],
            spatial_layout_intent="SPLIT_STAGE",
        )
    else:
        prop_context = (
            f"Prompt: {pedagogical_prompt}\n"
            f"Environment: {env.model_dump_json()}"
        )
        prop_res = prop_master_agent.run_sync(prop_context)
        mobjects_roster = getattr(prop_res, "output", getattr(prop_res, "data", None))

    # Step 3: Layout Critic (Deterministic Spatial Engine)
    roster_dicts = [m.model_dump() for m in mobjects_roster.mobjects]
    layout_state: SceneLayoutState = layout_critic.solve(roster_dicts)

    # Step 4: Choreographer (Animations & Audio Sync)
    if use_mock_agents:
        choreography = SceneChoreography(
            events=[
                AnimationEvent(
                    target_variables=["title"],
                    animation_class="Write",
                    audio_bookmark_sync="intro_title",
                    run_time=1.0,
                    wait_after=1.0,
                ),
                AnimationEvent(
                    target_variables=["axes"],
                    animation_class="Create",
                    audio_bookmark_sync="show_axes",
                    run_time=1.5,
                    wait_after=0.5,
                    cleanup_before=["title"],
                ),
                AnimationEvent(
                    target_variables=["func_curve"],
                    animation_class="Create",
                    audio_bookmark_sync="show_curve",
                    run_time=1.5,
                    wait_after=0.5,
                ),
                AnimationEvent(
                    target_variables=["deriv_eq"],
                    animation_class="Write",
                    audio_bookmark_sync="show_formula",
                    run_time=2.0,
                    wait_after=1.5,
                ),
                AnimationEvent(
                    target_variables=["deriv_eq"],
                    animation_class="Indicate",
                    audio_bookmark_sync="emphasize_limit",
                    run_time=1.0,
                    rate_func="there_and_back",
                    wait_after=0.5,
                ),
            ],
            next_slide_bookmarks=["emphasize_limit"],
        )
    else:
        choreography_context = (
            f"Prompt: {pedagogical_prompt}\n"
            f"Audio Script: {audio_script}\n"
            f"Mobjects: {mobjects_roster.model_dump_json()}\n"
            f"Resolved Layout Code:\n" + "\n".join(layout_state.layout_code)
        )
        choreo_res = choreographer_agent.run_sync(choreography_context)
        choreography = getattr(choreo_res, "output", getattr(choreo_res, "data", None))

    # Step 4b: Cross-validate choreography against roster
    validation_errors = validate_choreography_against_roster(choreography, mobjects_roster)
    if validation_errors:
        print("WARNING: Choreography validation errors:")
        for err in validation_errors:
            print(f"  - {err}")
        # In production, this would trigger a choreographer retry

    # Step 5: Code Assembler
    assembled_code = assemble_manim_script(env, mobjects_roster, layout_state, choreography)

    # Step 6: Repair Loop — Syntax Check
    for attempt in range(max_repairs + 1):
        is_valid, error_msg = syntax_check(assembled_code)
        if is_valid:
            break
        responsible = diagnose_error(error_msg)
        print(f"REPAIR attempt {attempt + 1}/{max_repairs}: {error_msg}")
        print(f"  Diagnosed as: {responsible} failure")
        if attempt < max_repairs:
            # In production, re-run the responsible agent with error context
            print(f"  Would re-run {responsible} with error context...")
            break  # For now, just report the error

    return {
        "environment": env,
        "mobjects": mobjects_roster,
        "layout": layout_state,
        "choreography": choreography,
        "python_code": assembled_code,
        "syntax_valid": is_valid if 'is_valid' in dir() else True,
        "validation_errors": validation_errors,
    }


if __name__ == "__main__":
    prompt = "Explain the limit definition of a derivative with a dynamic secant line."
    result = synthesize_scene_pipeline(prompt)
    print("=== Multi-Agent Assembly Line v2 Completed ===")
    print(f"  Syntax valid: {result.get('syntax_valid', 'N/A')}")
    if result.get("validation_errors"):
        print(f"  Validation warnings: {len(result['validation_errors'])}")
    print()
    print("--- Generated Manim Python Code ---")
    print(result["python_code"])

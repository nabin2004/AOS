"""Pydantic AI Web Chat UI Runner for AOS Human-In-The-Loop (HITL) Development.

Provides an interactive browser-based Chat UI using Pydantic AI's native `agent.to_web()`:
- Web-based human-in-the-loop tool approvals (`requires_approval=True`):
  * Checkpoint 1: Classification (topic, subject override e.g. math vs cs, animatability)
  * Checkpoint 2: Visual Plan (scenes.md review and approval)
  * Checkpoint 3: Code generation with Pyright LSP diagnostics & self-repair
  * Checkpoint 4: Local Manim video rendering
- Run via:
  uv run python dev_hitl_web.py [--reload]
  uv run uvicorn dev_hitl_web:app --host 127.0.0.1 --port 7932
  # When using uvicorn with --reload, exclude hitl_workspace so saves do not restart the server:
  uv run uvicorn dev_hitl_web:app --host 127.0.0.1 --port 7932 --reload --reload-dir app
  # or:
  uv run uvicorn dev_hitl_web:app --host 127.0.0.1 --port 7932 --reload --reload-exclude "hitl_workspace/*"
  uv run python dev_hitl.py --web
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, DeferredToolRequests, RunContext
from pydantic_ai.models.test import TestModel
from pydantic_ai.settings import ModelSettings
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from starlette.applications import Starlette

import app.agents.hitl_agents as hitl_agents
from app.agents.hitl_agents import (
    HitlAgentTools,
    HitlCodeExtractor,
    HitlLLMResolver,
    extract_manim_code,
    resolve_skill_reference_content,
)
from app.core.local_logging import (
    DEFAULT_LOG_DIR,
    DEFAULT_WORKSPACE_DIR,
    HitlRunStore,
    HitlTerminalObserver,
    HitlWorkspace,
    disable_logfire_remote,
)
from app.schemas.video_generation import VideoClassifyResponse
from app.services.latex_validator import run_latex_diagnostics
from app.services.lsp_service import run_pyright_lsp
from app.services.positioning_linter import lint_manim_positioning
from app.services.manim_code import preflight_manim_code
from app.skills import get_coder_skills, get_composer_skills, get_repair_skills, get_skills


HITL_WEB_SYSTEM_PROMPT = """\
You are the AOS Human-In-The-Loop (HITL) Director for Manim educational animation generation.
You interact directly with the human operator through this Web Chat UI to iteratively create mathematical, algorithmic, and scientific visualizations using Manim Community Edition.

PIPELINE STAGES & STREAMING WORKFLOW:
To ensure the operator sees every single action and skill loading in real-time in the UI, follow these steps sequentially:

1. Stage 1 — Classification & Animatability Checkpoint:
   - When the user asks to explain or animate an educational topic, first analyze it to determine:
     * `topic`: Clean title-cased topic (e.g., "Dijkstra's Algorithm", "Logarithms").
     * `subject`: Core domain ("math", "cs", "ai", "physics", or custom).
     * `animatable`: Boolean (True if dynamic visual motion benefits understanding).
     * `reason`: 1-2 sentences on visual elements.
   - You MUST call `checkpoint_approve_classification(topic, subject, animatable, reason)`.
   - IMPORTANT: This tool requires operator approval. The UI will pause and display an interactive card allowing the operator to verify or edit the subject (e.g. correcting "log" from CS to Math) before continuing.

2. Stage 2 — Visual Plan Composition Checkpoint:
   - Before composing, call `load_skill_reference(skill="manim-composer")` and/or `load_skill_reference(skill="manimce-best-practices", path="rules/positioning.md")` so the operator sees the pedagogical and ManimCE spatial layout skills being loaded in the UI stream.
   - Compose a comprehensive pedagogical scene-by-scene animation plan following both `manim-composer` and `manimce-best-practices` (scenes.md):
     * Title, Overview, Hook, Target Audience, Estimated Length, Key Insight
     * Narrative Arc
     * Scene 1, Scene 2, ... (Duration, Purpose, Visual Elements, Content, Narration Notes, Technical Notes)
     * In Technical Notes, explicitly specify layout positioning (.to_edge, .next_to, VGroup.arrange) and coordinate axes (Axes, c2p mapping) to ensure code synthesis is robust.
     * Transitions & Flow, Color Palette, and Mathematical Content
   - You MUST call `checkpoint_approve_visual_plan(topic, subject, plan_markdown)`.
   - IMPORTANT: This tool requires operator approval. The UI will display the plan for the operator to review, edit, or approve.

3. Stage 3 — Code Synthesis, Pyright LSP Diagnostics & Self-Repair:
   - Before coding, call `load_skill_reference(skill="manimce-best-practices")` so the operator sees the Manim Community Edition skill rules loading in the UI stream.
   - Next, call `synthesize_manim_code(topic, plan_markdown)` (or `generate_and_validate_manim_code(topic, plan_markdown)`) to produce the Manim scene.
   - Then call `validate_code_with_lsp(scene_name)` to run Pyright LSP diagnostics, AST preflight syntax check, and LaTeX checks, streaming the live report into the chat.
   - If any member errors, typing errors, or LaTeX delimiters fail, call `repair_manim_code(scene_name, error_feedback)` to automatically fix them.

4. Stage 4 — Local Video Rendering (Optional):
   - You can call `render_manim_scene(scene_name, quality)` to render the scene with `manim -ql` for instant preview.
   - This tool asks the operator for approval before launching the render.

Always be concise, collaborative, and transparent by streaming each step as a visible tool action.
"""


def create_hitl_web_agent(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    mock: bool = False,
    workspace_dir: Path | str | None = None,
    log_dir: Path | str | None = None,
) -> Agent[None, str]:
    """Create the orchestrated HITL Pydantic AI agent configured for Web Chat UI."""
    workspace = HitlWorkspace(workspace_dir=workspace_dir or DEFAULT_WORKSPACE_DIR)
    run_store = HitlRunStore(log_dir=log_dir or DEFAULT_LOG_DIR)

    if mock:
        model = TestModel(
            custom_output_args={
                "topic": "Fourier Transform",
                "subject": "math",
                "animatable": True,
                "reason": "Decomposition of waveforms into frequencies via rotating vectors.",
            }
        )
    else:
        resolver = HitlLLMResolver()
        model = resolver.build_model(model_name=model_name, base_url=base_url, api_key=api_key)

    agent = Agent(
        model=model,
        system_prompt=HITL_WEB_SYSTEM_PROMPT,
        name="AOS HITL Web Director",
        capabilities=[get_skills(include=["manim-composer", "manimce-best-practices", "manim-render"])],
        output_type=[str, DeferredToolRequests],
        retries=2,
        model_settings=ModelSettings(max_tokens=hitl_agents.HITL_MAX_TOKENS),
    )

    # ── Checkpoint Tool 1: Classification (Requires Approval) ─────────────────
    # ── Checkpoint Tool 1: Classification (Requires Approval) ─────────────────
    @agent.tool_plain(requires_approval=True)
    def checkpoint_approve_classification(
        topic: str = "",
        subject: str = "cs",
        animatable: bool | str = True,
        reason: str = "",
        **kwargs: Any,
    ) -> str:
        """[HITL Checkpoint 1] Request human operator approval for topic and subject classification.

        The operator can approve, reject, or edit the fields directly in the Web Chat UI
        (e.g., correcting subject from 'cs' to 'math' if logarithms were mistaken for logging).
        """
        if isinstance(animatable, str):
            animatable_bool = animatable.strip().lower() in ("true", "1", "yes", "y")
        else:
            animatable_bool = bool(animatable)

        active_topic = topic or kwargs.get("title", "")
        if not active_topic:
            saved_input = workspace.load_input() or {}
            active_topic = saved_input.get("topic") or saved_input.get("text") or "Educational Topic"

        scene_type = kwargs.get("scene_type", "Scene")
        needs_3d = kwargs.get("needs_3d", False)
        needs_updaters = kwargs.get("needs_updaters", False)
        needs_axes = kwargs.get("needs_axes", False)
        needs_camera_movement = kwargs.get("needs_camera_movement", False)
        needs_timing_control = kwargs.get("needs_timing_control", False)
        needs_graphing = kwargs.get("needs_graphing", False)

        resp = VideoClassifyResponse(
            animatable=animatable_bool,
            subject=subject or "cs",
            topic=active_topic,
            reason=reason or f"Topic '{active_topic}' in {subject}",
            scene_type=scene_type,
            needs_3d=needs_3d,
            needs_updaters=needs_updaters,
            needs_axes=needs_axes,
            needs_camera_movement=needs_camera_movement,
            needs_timing_control=needs_timing_control,
            needs_graphing=needs_graphing,
        )
        workspace.save_classification(resp, query=active_topic)
        run_store.record_run(
            stage="classify",
            topic=active_topic,
            model_name="mock:TestModel" if mock else (model_name or "default"),
            duration=0.0,
            success=True,
            artifacts={"classification": resp.model_dump()},
        )
        return (
            f"Classification confirmed by operator:\n"
            f"- Topic: {active_topic}\n"
            f"- Subject Domain: {subject or 'cs'}\n"
            f"- Animatable: {animatable_bool}\n"
            f"- Scene Type: {scene_type}\n"
            f"- Tools/Flags: 3D={needs_3d}, Updaters={needs_updaters}, Axes={needs_axes}, Camera={needs_camera_movement}, Timing={needs_timing_control}, Graphing={needs_graphing}\n"
            f"- Saved to: {workspace.classification_file.name}\n\n"
            f"You may now proceed to Stage 2: compose the visual plan (scenes.md) and submit it to checkpoint_approve_visual_plan."
        )

    # ── Checkpoint Tool 2: Visual Plan (Requires Approval) ────────────────────
    @agent.tool_plain(requires_approval=True)
    def checkpoint_approve_visual_plan(
        topic: str = "",
        subject: str = "",
        plan_markdown: str = "",
        plan: str = "",
        scenes: str = "",
        **kwargs: Any,
    ) -> str:
        """[HITL Checkpoint 2] Request human operator approval for the scenes.md visual plan.

        The operator can review the narrative progression, scene elements, and timings in the UI.
        """
        content = plan_markdown or plan or scenes or kwargs.get("content", "") or kwargs.get("plan_content", "")
        if not content:
            return "Error: No plan markdown provided. Please include the scene-by-scene visual plan."

        saved_class = workspace.load_classification() or {}
        active_topic = topic or saved_class.get("topic") or "Educational Topic"
        active_subject = subject or saved_class.get("subject") or "general"

        workspace.save_plan(content, topic=active_topic)
        run_store.record_run(
            stage="compose",
            topic=active_topic,
            model_name="mock:TestModel" if mock else (model_name or "default"),
            duration=0.0,
            success=True,
            artifacts={"plan": content},
        )
        return (
            f"Visual plan confirmed by operator for '{active_topic}'.\n"
            f"- Saved to: {workspace.plan_md_file.name} and {workspace.plan_json_file.name}\n\n"
            f"You may now proceed to Stage 3: call synthesize_manim_code or generate_and_validate_manim_code."
        )

    # ── Skill Loader Tool: Stream Skill Rules to UI ───────────────────────────
    @agent.tool_plain
    def load_skill_reference(skill: str, path: str = "") -> str:
        """Stream and load pedagogical or Manim Community Edition skill knowledge into the UI session.

        Args:
            skill: The skill to load ('manim-composer' for planning, 'manimce-best-practices' for coding).
            path: Optional sub-rule path (e.g. 'rules/positioning.md', 'references/scene-examples.md', 'narrative-patterns.md').
        """
        skill_name = (skill or "").strip().lower()
        if "composer" in skill_name:
            if path:
                content = resolve_skill_reference_content(path=path)
                return f"[Skill Loaded: manim-composer/{path}]\n{content[:600]}..."
            return (
                "Loaded Skill: manim-composer (Pedagogical Animation Composer)\n"
                "- Core Principles: 3Blue1Brown visual intuition, cognitive load management\n"
                "- Required Format: scenes.md (Overview, Narrative Arc, Scenes 1..N, Transitions, Color Palette)\n"
                "- Active References: references/narrative-patterns.md, references/visual-techniques.md"
            )
        elif "manim" in skill_name or "coder" in skill_name or "best-practices" in skill_name:
            if path:
                content = resolve_skill_reference_content(path=path)
                return f"[Skill Loaded: manimce-best-practices/{path}]\n{content[:600]}..."
            return (
                "Loaded Skill: manimce-best-practices (Manim Community Edition v0.18+)\n"
                "- 3D Coordinates: [x, y, 0] strictly (never 2D [x, y])\n"
                "- LaTeX: Raw strings r'...' for all MathTex / Tex\n"
                "- Positioning: Safe spacing with next_to(..., buff=...), to_edge(UP), VGroup.arrange()\n"
                "- LSP Guardrails: Strict Pyright validation, no hallucinated classes or deprecated methods"
            )
        elif any(k in skill_name for k in ("position", "axe", "transform", "mobject", "shape", "color")):
            target_path = path or (f"rules/{skill_name}.md" if not skill_name.endswith(".md") else skill_name)
            content = resolve_skill_reference_content(path=target_path)
            return f"[Skill Loaded: manimce-best-practices/{target_path}]\n{content[:600]}..."
        else:
            return resolve_skill_reference_content(path=path or skill)

    # ── Granular Tool: Synthesize Code ────────────────────────────────────────
    @agent.tool
    async def synthesize_manim_code(
        ctx: RunContext[Any],
        topic: str,
        plan_markdown: str | None = None,
    ) -> str:
        """Synthesize executable Manim Community Edition Python code for the approved visual plan."""
        if not plan_markdown:
            loaded_plan, _ = workspace.load_plan()
            plan_markdown = loaded_plan or ""

        if not plan_markdown:
            return "Error: No visual plan found in workspace or arguments. Please compose and approve a visual plan first."

        clean_name = topic.replace(" ", "").replace("-", "").replace("'", "")
        scene_name = f"{clean_name}Scene"

        if mock:
            from dev_hitl import MOCK_VALID_CODE
            code = MOCK_VALID_CODE
            scene_name = "FourierTransformScene"
        else:
            coder_agent = hitl_agents.get_coder_agent(
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
                capabilities=[get_coder_skills()],
            )
            deps = hitl_agents.HitlCoderDeps(plan=plan_markdown, scene_name=scene_name)
            tier1_context = hitl_agents.get_manimce_tier1_preinjected_context()
            coder_prompt = (
                f"Topic: {topic}\n\n"
                f"Visual Plan (scenes.md):\n{plan_markdown}\n\n"
                f"{tier1_context}\n\n"
                "Generate complete, executable Manim Community Edition Python code for this animation. "
                "Follow the pre-injected Tier 1 rules strictly: "
                "NEVER use raw coordinate literals or manual float shifts. Use relative layouts (.next_to, .arrange, .to_edge) "
                "or axes.c2p(), and avoid hallucinated APIs."
            )
            try:
                res = await coder_agent.run(
                    coder_prompt,
                    deps=deps,
                    model_settings=ModelSettings(max_tokens=hitl_agents.HITL_MAX_TOKENS),
                )
                raw_output = getattr(res, "output", getattr(res, "data", "")) or ""
                code, detected_scene = hitl_agents.extract_manim_code(raw_output, default_scene=scene_name)
                if detected_scene:
                    scene_name = detected_scene
            except Exception as exc:
                # If generation hit an error but user already edited/saved scene.py, fallback to workspace code
                existing_code, existing_scene = workspace.load_code()
                if existing_code and "def construct" in existing_code:
                    code = existing_code
                    scene_name = existing_scene or scene_name
                else:
                    return f"Code generation encountered an error: {exc}"

        if not code:
            return "Code synthesis did not yield valid Python source code."

        workspace.save_code(code, scene_name=scene_name, topic=topic)
        line_count = len(code.splitlines())
        return (
            f"Manim code synthesized successfully for `{scene_name}` ({line_count} lines)!\n"
            f"- Saved to: `{workspace.scene_file.name}`\n"
            f"- Primary Scene: `{scene_name}`\n\n"
            f"```python\n{code}\n```\n\n"
            f"Now call validate_code_with_lsp(scene_name='{scene_name}') to run Pyright LSP diagnostics."
        )

    # ── Granular Tool: Validate with Pyright LSP ──────────────────────────────
    @agent.tool_plain
    def validate_code_with_lsp(scene_name: str | None = None) -> str:
        """Run Pyright LSP diagnostics, AST preflight syntax check, and LaTeX delimiter validation on the current scene code."""
        loaded_code, loaded_scene = workspace.load_code()
        if not loaded_code:
            return "Error: No scene.py code found in workspace to validate."

        target_scene = scene_name or loaded_scene or "GeneratedScene"

        latex_diags = run_latex_diagnostics(loaded_code)
        lsp_report = run_pyright_lsp(loaded_code, is_code=True)
        pos_report = lint_manim_positioning(loaded_code)
        workspace.save_preflight(None, None, lsp_report)

        has_issues = bool(
            (lsp_report and lsp_report.has_errors)
            or bool(latex_diags)
            or (pos_report and pos_report.has_errors)
        )

        diag_lines = [
            f"Pyright LSP Validation Report (with Positioning Lint) for `{target_scene}`:",
            f"- Pyright LSP: {lsp_report.error_count} error(s), {lsp_report.warning_count} warning(s)",
            f"- Positioning Linter: {len(pos_report.issues)} issue(s) ({pos_report.relative_layout_calls} relative layout calls)",
            f"- LaTeX Validation: {len(latex_diags)} delimiter issue(s)",
        ]

        if not has_issues and not pos_report.issues:
            diag_lines.append("\nAll Manim classes, mobject methods, and positioning layouts are clean and error-free! Ready for render.")
        else:
            diag_lines.append("\nDetected Issues:")
            if lsp_report and lsp_report.has_errors:
                diag_lines.append(f"Pyright LSP:\n{lsp_report.format_feedback()}")
            if pos_report.issues:
                diag_lines.append(f"Positioning Lint:\n{pos_report.format_feedback()}")
            if latex_diags:
                diag_lines.append("LaTeX Diagnostics:\n" + "\n".join(f"- Line {d.line}: {d.message} in '{d.tex_string}'" for d in latex_diags))
            diag_lines.append("\nPlease call repair_manim_code to auto-fix these diagnostics.")

        return "\n".join(diag_lines)

    # ── Granular Tool: Repair Manim Code ──────────────────────────────────────
    @agent.tool
    async def repair_manim_code(
        ctx: RunContext[Any],
        error_feedback: str | None = None,
        scene_name: str | None = None,
    ) -> str:
        """Auto-repair the current Manim scene code against compiler and LSP diagnostic errors."""
        loaded_code, loaded_scene = workspace.load_code()
        if not loaded_code:
            return "Error: No scene code found in workspace to repair."

        target_scene = scene_name or loaded_scene or "GeneratedScene"
        error_bundle = error_feedback or "LSP errors detected in construct method."

        if mock:
            from dev_hitl import MOCK_VALID_CODE
            repaired_code = MOCK_VALID_CODE
            rep_scene = target_scene
            workspace.save_code(repaired_code, scene_name=rep_scene, topic="")
            return (
                f"Code auto-repaired successfully!\n"
                f"- Scene: `{rep_scene}`\n"
                f"- Post-repair LSP Status: 0 error(s), 0 warning(s)\n\n"
                f"```python\n{repaired_code}\n```"
            )

        repair_agent = hitl_agents.get_repair_agent(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            capabilities=[get_repair_skills()],
        )
        rep_deps = hitl_agents.HitlRepairDeps(error=error_bundle, current_code=loaded_code)
        rep_prompt = (
            f"Repair the following Manim code against compiler and LSP errors:\n\n"
            f"{error_bundle}\n\n"
            f"Current Code:\n```python\n{loaded_code}\n```"
        )
        try:
            rep_res = await repair_agent.run(
                rep_prompt,
                deps=rep_deps,
                model_settings=ModelSettings(max_tokens=hitl_agents.HITL_MAX_TOKENS),
            )
            rep_raw = getattr(rep_res, "output", getattr(rep_res, "data", "")) or ""
            repaired_code, rep_scene = hitl_agents.extract_manim_code(rep_raw, default_scene=target_scene)
            if repaired_code:
                workspace.save_code(repaired_code, scene_name=rep_scene or target_scene, topic="")
                new_lsp = run_pyright_lsp(repaired_code, is_code=True)
                return (
                    f"Code auto-repaired successfully!\n"
                    f"- Scene: `{rep_scene or target_scene}`\n"
                    f"- Post-repair LSP Status: {new_lsp.error_count} error(s), {new_lsp.warning_count} warning(s)\n\n"
                    f"```python\n{repaired_code}\n```"
                )
        except Exception as exc:
            return f"Repair pass failed: {exc}"

        return "Repair pass completed without changes."

    # ── Stage 3: Code Synthesis, LSP Diagnostics & Self-Repair ───────────────
    @agent.tool
    async def generate_and_validate_manim_code(
        ctx: RunContext[Any],
        topic: str,
        plan_markdown: str | None = None,
    ) -> str:
        """Synthesize complete Manim Community Edition Python code, validate with Pyright LSP and LaTeX checker, and auto-repair any issues."""
        if not plan_markdown:
            loaded_plan, _ = workspace.load_plan()
            plan_markdown = loaded_plan or ""

        if not plan_markdown:
            return "Error: No visual plan found in workspace or arguments. Please compose and approve a visual plan first."

        code = ""
        clean_name = topic.replace(" ", "").replace("-", "").replace("'", "")
        scene_name = f"{clean_name}Scene"

        if mock:
            from dev_hitl import MOCK_VALID_CODE
            code = MOCK_VALID_CODE
            scene_name = "FourierTransformScene"
        else:
            coder_agent = hitl_agents.get_coder_agent(
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
                capabilities=[get_coder_skills()],
            )
            deps = hitl_agents.HitlCoderDeps(plan=plan_markdown, scene_name=scene_name)
            tier1_context = hitl_agents.get_manimce_tier1_preinjected_context()
            coder_prompt = (
                f"Topic: {topic}\n\n"
                f"Visual Plan (scenes.md):\n{plan_markdown}\n\n"
                f"{tier1_context}\n\n"
                "Generate complete, executable Manim Community Edition Python code for this animation. "
                "Follow the pre-injected Tier 1 rules strictly: "
                "NEVER use raw coordinate literals or manual float shifts. Use relative layouts (.next_to, .arrange, .to_edge) "
                "or axes.c2p(), and avoid hallucinated APIs."
            )
            try:
                res = await coder_agent.run(
                    coder_prompt,
                    deps=deps,
                    model_settings=ModelSettings(max_tokens=hitl_agents.HITL_MAX_TOKENS),
                )
                raw_output = getattr(res, "output", getattr(res, "data", "")) or ""
                code, detected_scene = hitl_agents.extract_manim_code(raw_output, default_scene=scene_name)
                if detected_scene:
                    scene_name = detected_scene
            except Exception as exc:
                # If generation hit an error but user already edited/saved scene.py, fallback to workspace code
                existing_code, existing_scene = workspace.load_code()
                if existing_code and "def construct" in existing_code:
                    code = existing_code
                    scene_name = existing_scene or scene_name
                else:
                    return f"Code generation encountered an error: {exc}"

        if not code:
            return "Code synthesis did not yield valid Python source code."

        # 1. (Removed AST Preflight Check)
        
        # 2. LaTeX Validation
        latex_diags = run_latex_diagnostics(code)

        # 3. Pyright LSP Diagnostics Check
        lsp_report = run_pyright_lsp(code, is_code=True)

        # 4. Positioning Linter Check
        pos_report = lint_manim_positioning(code)

        # 5. Automatic Repair Pass if Diagnostics Fail
        repair_pass_count = 0
        needs_repair = bool(
            (lsp_report and lsp_report.has_errors)
            or bool(latex_diags)
            or (pos_report and pos_report.has_errors)
        )

        if needs_repair and not mock:
            error_sections: list[str] = []
            if lsp_report and lsp_report.has_errors:
                error_sections.append(f"Pyright LSP Diagnostics:\n{lsp_report.format_feedback()}")
            if pos_report.issues:
                error_sections.append(f"Positioning Lint Feedback:\n{pos_report.format_feedback()}")
            if latex_diags:
                latex_feedback = "\n".join(f"- Line {d.line}: {d.message} in '{d.tex_string}'" for d in latex_diags)
                error_sections.append(f"LaTeX Delimiter Diagnostics:\n{latex_feedback}")

            error_bundle = "\n\n".join(error_sections)

            repair_agent = hitl_agents.get_repair_agent(
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
                capabilities=[get_repair_skills()],
            )
            rep_deps = hitl_agents.HitlRepairDeps(error=error_bundle, current_code=code)
            rep_prompt = (
                f"Repair the following Manim code against compiler and LSP errors:\n\n"
                f"{error_bundle}\n\n"
                f"Current Code:\n```python\n{code}\n```"
            )
            try:
                rep_res = await repair_agent.run(rep_prompt, deps=rep_deps)
                rep_raw = getattr(rep_res, "output", getattr(rep_res, "data", "")) or ""
                repaired_code, rep_scene = HitlCodeExtractor.extract(rep_raw, default_scene=scene_name)
                if repaired_code:
                    code = repaired_code
                    if rep_scene:
                        scene_name = rep_scene
                    repair_pass_count = 1
                    # Re-run LSP to verify fixes
                    lsp_report = run_pyright_lsp(code, is_code=True)
            except Exception:
                pass

        # Save artifacts to workspace
        workspace.save_code(code, scene_name=scene_name, topic=topic)
        workspace.save_preflight(None, None, lsp_report)

        line_count = len(code.splitlines())
        lsp_summary = (
            f"{lsp_report.error_count} error(s), {lsp_report.warning_count} warning(s)"
            if lsp_report
            else "LSP skipped"
        )
        repair_tag = f" (Auto-repaired in {repair_pass_count} pass)" if repair_pass_count > 0 else ""

        return (
            f"Manim code synthesized and verified{repair_tag}!\n"
            f"- Scene Class: `{scene_name}`\n"
            f"- Lines of Code: {line_count}\n"
            f"- Pyright LSP Status: {lsp_summary}\n"
            f"- Saved to: `{workspace.scene_file.name}` and `{workspace.code_json_file.name}`\n\n"
            f"```python\n{code}\n```\n\n"
            f"You may now call render_manim_scene(scene_name='{scene_name}') to render the local preview video."
        )

    # ── Checkpoint Tool 4: Rendering (Requires Approval) ─────────────────────
    @agent.tool_plain(requires_approval=True)
    def render_manim_scene(
        scene_name: str,
        quality: str = "ql",
    ) -> str:
        """[HITL Checkpoint 4] Render the generated Manim scene locally with 'manim -ql'."""
        loaded_code, loaded_scene = workspace.load_code()
        if not loaded_code:
            return "Error: No scene code found in workspace to render."

        actual_scene = scene_name or loaded_scene or "GeneratedScene"
        from dev_hitl import run_local_render_check

        obs = HitlTerminalObserver(mock_mode=mock)
        video_path = run_local_render_check(loaded_code, actual_scene, obs, workspace=workspace)
        if video_path and video_path.exists():
            return (
                f"Video rendered successfully!\n"
                f"- Output Video: {video_path}\n"
                f"- Size: {video_path.stat().st_size} bytes\n"
                f"- Scene: `{actual_scene}`"
            )
        return (
            f"Render completed for scene `{actual_scene}`. "
            f"Check hitl_workspace directory for render logs and output files."
        )

    # ── Helper Tool: Inspect Workspace ───────────────────────────────────────
    @agent.tool_plain
    def inspect_hitl_workspace() -> str:
        """Inspect the current hitl_workspace directory: active topic, files present, and stage status."""
        artifacts = workspace.list_artifacts()
        status_items = [
            f"- {name}: {'EXISTS' if p.exists() else 'MISSING'} ({p.name})"
            for name, p in artifacts.items()
        ]
        return "Current hitl_workspace status:\n" + "\n".join(status_items)

    # ── Helper Tool: Read Skill Reference ────────────────────────────────────
    @agent.tool_plain
    def read_skill_reference(path: str = "") -> str:
        """Read a reference file from the manim-composer or manimce-best-practices skills (e.g. 'rules/positioning.md', 'narrative-patterns.md')."""
        return resolve_skill_reference_content(path=path)

    return agent


def create_hitl_web_app(
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    mock: bool = False,
    workspace_dir: Path | str | None = None,
    log_dir: Path | str | None = None,
    allowed_hosts: list[str] | None = None,
) -> Starlette:
    """Create the Starlette ASGI web chat application using Pydantic AI's native to_web()."""
    disable_logfire_remote()

    agent = create_hitl_web_agent(
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        mock=mock,
        workspace_dir=workspace_dir,
        log_dir=log_dir,
    )

    hosts = allowed_hosts or ["127.0.0.1", "localhost", "0.0.0.0", "[::1]"]

    return agent.to_web(
        allowed_hosts=hosts,
        instructions="Always guide the operator iteratively through the 4 HITL checkpoints: Classification -> Visual Plan -> Code & LSP Diagnostics -> Video Render.",
    )


# Module-level ASGI app instance for uvicorn (e.g. `uvicorn dev_hitl_web:app`)
app = create_hitl_web_app()


def run_web_server(
    host: str = "127.0.0.1",
    port: int = 7932,
    open_browser: bool = True,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    mock: bool = False,
    workspace_dir: Path | str | None = None,
    log_dir: Path | str | None = None,
    reload: bool = False,
) -> None:
    """Run the ASGI Web Chat server using uvicorn and open the browser."""
    import uvicorn

    web_app = create_hitl_web_app(
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        mock=mock,
        workspace_dir=workspace_dir,
        log_dir=log_dir,
        allowed_hosts=[host, "localhost", "127.0.0.1", "0.0.0.0"],
    )

    url = f"http://{host}:{port}"
    console = Console()
    console.print(
        Panel(
            f"[bold green]AOS Human-In-The-Loop Web Chat UI[/bold green]\n\n"
            f"[bold white]Server URL:[/bold white] [bold cyan underline]{url}[/bold cyan underline]\n"
            f"[bold white]Mode:[/bold white]       {'MOCK (TestModel)' if mock else 'LIVE LLM'}\n"
            f"[bold white]Workspace:[/bold white]  {workspace_dir or DEFAULT_WORKSPACE_DIR}\n\n"
            "[dim]Native Pydantic AI Tool Approvals are active:[/dim]\n"
            "[dim]• Checkpoint 1 (Classification: subject/topic approval)\n"
            "• Checkpoint 2 (Visual Plan: scenes.md review)\n"
            "• Checkpoint 3 (Pyright LSP diagnostics & self-repair)\n"
            "• Checkpoint 4 (Local preview render approval)[/dim]",
            title="[bold magenta]\U0001f310 AOS HITL Web Studio[/bold magenta]",
            box=ROUNDED,
            style="magenta",
            padding=(1, 2),
        )
    )

    if open_browser:
        def _open():
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:
                pass

        threading.Thread(target=_open, daemon=True).start()

    if reload:
        uvicorn.run(
            "dev_hitl_web:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=["app"],
            reload_excludes=["hitl_workspace", "hitl_workspace/*", "hitl_workspace/**", ".dev_logs/*"],
            log_level="info",
        )
    else:
        uvicorn.run(web_app, host=host, port=port, log_level="info")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AOS HITL Web Chat UI — Interactive browser-based agent development studio.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7932, help="Port to bind to (default: 7932)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes (excluding hitl_workspace)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")
    parser.add_argument("--mock", action="store_true", help="Run with Pydantic AI TestModel (offline, 0 tokens)")
    parser.add_argument(
        "-m", "--model",
        default=os.getenv("AI_MODEL") or os.getenv("AOS_OPENAI_MODEL") or "nvidia/nemotron-3-ultra-550b-a55b:free",
        help="LLM model override",
    )
    parser.add_argument(
        "-b", "--base-url",
        default=os.getenv("AOS_OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        help="LLM base URL / endpoint",
    )
    parser.add_argument(
        "-k", "--api-key",
        default=os.getenv("OPENROUTER_API_KEY", "") or os.getenv("AOS_OPENAI_API_KEY", ""),
        help="API key for OpenRouter or custom endpoint",
    )
    parser.add_argument("--workspace-dir", default=None, help="Custom workspace directory")
    parser.add_argument("--log-dir", default=None, help="Custom log directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_web_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        model_name=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        mock=args.mock,
        workspace_dir=args.workspace_dir,
        log_dir=args.log_dir,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

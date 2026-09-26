"""Frictionless local development and test runner for Pydantic AI HITL pipeline.

Run and test classifier, composer, coder, and self-correcting repair agents locally
with rich terminal UI, AST preflight diagnostics, and local JSON logging (no Logfire).

Usage examples:
    # 1. Full pipeline end-to-end with real model:
    uv run python dev_hitl.py "Explain the Fourier Transform"

    # 2. Test completely offline with Pydantic AI TestModel (0 token cost):
    uv run python dev_hitl.py --mock "Taylor Series Approximation"

    # 3. Test only classification:
    uv run python dev_hitl.py --stage classify "How does Dijkstra's Algorithm work?"

    # 4. Test only plan composition:
    uv run python dev_hitl.py --stage compose --topic "Binary Search"

    # 5. Test only code synthesis:
    uv run python dev_hitl.py --stage code --topic "Exponential Growth"

    # 6. Test preflight AST validator & deterministic fixer on any python file:
    uv run python dev_hitl.py --stage preflight --file broken_scene.py

    # 7. Test self-correcting repair agent with injected mobject indexing bug:
    uv run python dev_hitl.py --stage repair --inject-mobject-bug

    # 8. Inspect latest run log:
    uv run python dev_hitl.py --inspect-last
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")
    if (backend_dir.parents[2] / "agents" / ".env").exists():
        load_dotenv(backend_dir.parents[2] / "agents" / ".env")
except Exception:
    pass


if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.models.test import TestModel
from pydantic_ai.settings import ModelSettings
from rich.box import ROUNDED, SIMPLE
from rich.panel import Panel
from rich.table import Table

import app.agents.hitl_agents as hitl_agents
from app.agents.error_classifier import classify_error, get_repair_guidance
from app.core.local_logging import (
    DEFAULT_WORKSPACE_DIR,
    HitlRunStore,
    HitlTerminalObserver,
    HitlWorkspace,
    create_hitl_local_dev_hooks,
    disable_logfire_remote,
)
from app.skills import get_coder_skills, get_composer_skills, get_repair_skills
from app.schemas.video_generation import VideoClassifyResponse
from app.services.lsp_service import run_pyright_lsp, LspDiagnosticReport
from app.services.manim_code import preflight_manim_code, repair_manim_code


# ── Sample Fixtures for Mock / Offline Mode ────────────────────────────────────

MOCK_TOPIC = "Fourier Transform"
MOCK_TEXT = """\
The Fourier Transform is a mathematical technique that decomposes any waveform
or function into an infinite sum of sinusoidal frequencies.
Formula:
$$ \\hat{f}(\\xi) = \\int_{-\\infty}^{\\infty} f(x) e^{-2\\pi i x \\xi} dx $$
"""

MOCK_PLAN = """\
# Visualizing the Fourier Transform

## Overview
- **Topic**: Fourier Transform
- **Hook**: How can any complex sound or wave be split into pure musical notes?
- **Target Audience**: Undergraduate STEM learners
- **Estimated Length**: ~30 seconds
- **Key Insight**: The Fourier Transform acts like a mathematical prism splitting light into frequencies.

## Narrative Arc
We show a composite wave, wrap it around a circle, and reveal the center of mass frequency peak.

---

## Scene 1: Composite Signal
**Duration**: ~10 seconds
**Purpose**: Introduce a complex wave formed by adding two sine waves.
### Visual Elements
- `Axes` coordinate frame.
- Two individual sine curves in TEAL and YELLOW.
- Summed waveform in BLUE_C.

---

## Scene 2: The Fourier Integral
**Duration**: ~15 seconds
**Purpose**: Present the mathematical formula and its visual meaning.
### Visual Elements
- MathTex formula: `\\hat{f}(\\xi) = \\int_{-\\infty}^{\\infty} f(x) e^{-2\\pi i x \\xi} dx`
- Frequency spectrum plot with distinct spikes.

## Color Palette
- Primary: BLUE_C
- Secondary: YELLOW
- Accent: TEAL
"""

MOCK_VALID_CODE = """\
from manim import *

class FourierTransformScene(Scene):
    def construct(self):
        title = Text("The Fourier Transform", font_size=40).to_edge(UP, buff=0.5)
        formula = MathTex(
            r"\\hat{f}(\\xi) = \\int_{-\\infty}^{\\infty} f(x) e^{-2\\pi i x \\xi} dx",
            font_size=36,
        ).shift(UP * 0.5)
        note = Text("Decomposing signals into frequencies", font_size=24, color=YELLOW)
        note.next_to(formula, DOWN, buff=0.5)

        self.play(Write(title))
        self.play(FadeIn(formula, shift=UP * 0.2))
        self.play(Write(note))
        self.wait(1.5)
        self.play(FadeOut(formula), FadeOut(note), FadeOut(title))
"""

MOCK_BROKEN_CODE_MOBJECT = """\
from manim import *

class BrokenMobjectScene(Scene):
    def construct(self):
        title = Text("Mobject Index Test", font_size=40).to_edge(UP)
        formula = MathTex(r"E = m c^2")
        # Bug: out of range index on a single-string MathTex!
        square = formula[5]
        square.set_color(RED)

        self.play(Write(title))
        self.play(Write(formula))
        self.wait(1)
"""


# ── HITL Human Approval Gate ──────────────────────────────────────────────────

def hitl_approve(
    observer: "HitlTerminalObserver",
    stage_label: str,
    summary: str,
    *,
    auto_approve: bool = False,
) -> bool:
    """Prompt the human operator to approve the stage output before continuing.

    Returns True to proceed, False to abort the pipeline.
    Set auto_approve=True (via --no-hitl-approval) to skip for CI/batch runs.
    """
    if auto_approve:
        observer.step("HITL", f"Auto-approved [{stage_label}] (--no-hitl-approval)")
        return True

    from rich.prompt import Prompt
    from rich.panel import Panel
    from rich.box import ROUNDED

    observer.console.print(
        Panel(
            f"[bold cyan]{summary}[/bold cyan]\n\n"
            "[bold]Proceed to next stage?[/bold]  "
            "[green]y[/green] = yes / [red]n[/red] = abort / "
            "[yellow]s[/yellow] = skip this stage",
            title=f"[bold magenta]\U0001f9d1 HITL Checkpoint — {stage_label}[/bold magenta]",
            box=ROUNDED,
            style="magenta",
            padding=(0, 2),
        )
    )
    try:
        choice = Prompt.ask(
            "[bold magenta]Your decision[/bold magenta]",
            choices=["y", "n", "s"],
            default="y",
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        observer.warning("HITL prompt interrupted — aborting pipeline.")
        return False

    if choice == "n":
        observer.error(f"Pipeline aborted by operator at [{stage_label}] checkpoint.")
        return False
    if choice == "s":
        observer.warning(f"Stage [{stage_label}] skipped by operator.")
        return False
    return True


def hitl_classify_checkpoint(
    observer: "HitlTerminalObserver",
    classify_res: VideoClassifyResponse,
    current_topic: str,
    current_text: str,
    *,
    workspace: HitlWorkspace | None = None,
    run_store: HitlRunStore | None = None,
    auto_approve: bool = False,
) -> tuple[bool, str, VideoClassifyResponse]:
    """Prompt the human operator to approve or override the classification.

    Allows overriding subject (and optionally topic) when the model misclassifies
    (e.g., classifying 'log' as CS instead of Math).

    Returns:
        (proceed: bool, updated_topic: str, updated_classification: VideoClassifyResponse)
    """
    if auto_approve:
        observer.step("HITL", "Auto-approved [CLASSIFY] (--no-hitl-approval)")
        return True, current_topic, classify_res

    from rich.prompt import Prompt
    from rich.panel import Panel
    from rich.table import Table
    from rich.box import ROUNDED

    summary = (
        f"Topic: [bold]{current_topic}[/bold]  |  "
        f"Animatable: {'YES' if classify_res.animatable else 'NO'}  |  "
        f"Subject: [bold cyan]{classify_res.subject}[/bold cyan]"
    )
    if classify_res.reason:
        summary += f"\n[dim]Reason: {classify_res.reason}[/dim]"

    observer.console.print(
        Panel(
            f"[bold cyan]{summary}[/bold cyan]\n\n"
            "[bold]Proceed to next stage?[/bold]  "
            "[green]y[/green] = yes / [yellow]n[/yellow] = change subject / "
            "[red]a[/red] = abort / [dim]s[/dim] = skip this stage",
            title="[bold magenta]\U0001f9d1 HITL Checkpoint — CLASSIFY[/bold magenta]",
            box=ROUNDED,
            style="magenta",
            padding=(0, 2),
        )
    )

    try:
        choice = Prompt.ask(
            "[bold magenta]Your decision[/bold magenta]",
            choices=["y", "n", "a", "s"],
            default="y",
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        observer.warning("HITL prompt interrupted — aborting pipeline.")
        return False, current_topic, classify_res

    if choice == "y":
        return True, current_topic, classify_res

    if choice == "a":
        observer.error("Pipeline aborted by operator at [CLASSIFY] checkpoint.")
        return False, current_topic, classify_res

    if choice == "s":
        observer.warning("Stage [CLASSIFY] skipped by operator.")
        return False, current_topic, classify_res

    # choice == "n": operator wants to change subject / classification
    observer.step("HITL", "Manual classification override requested.")

    available_subjects = [
        ("1", "math", "Mathematics (Calculus, Linear Algebra, Logarithms, Geometry, etc.)"),
        ("2", "cs", "Computer Science (Algorithms, Data Structures, Networks, Systems)"),
        ("3", "ai", "Artificial Intelligence & ML (Neural Nets, Transformers, Optimization)"),
        ("4", "physics", "Physics (Mechanics, Electromagnetism, Quantum, Optics, Waves)"),
        ("5", "other", "Custom Subject (Enter custom subject domain)"),
    ]

    table = Table(
        title="[bold yellow]Available Subjects for Manim Animation[/bold yellow]",
        box=ROUNDED,
        show_header=True,
    )
    table.add_column("Key", style="bold green", width=5, justify="center")
    table.add_column("Subject ID", style="bold cyan", width=12)
    table.add_column("Domain / Description", style="white")

    for key, subj_id, desc in available_subjects:
        table.add_row(key, subj_id, desc)
    table.add_row("0", "abort", "[dim red]Abort pipeline[/dim red]")

    observer.console.print(table)

    default_key = "1" if classify_res.subject != "math" else "2"
    try:
        subj_choice = Prompt.ask(
            "[bold yellow]Select correct subject[/bold yellow] (1-5, subject name, or 0 to abort)",
            default=default_key,
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        observer.warning("Input interrupted — aborting pipeline.")
        return False, current_topic, classify_res

    if subj_choice in ("0", "abort", "q", "quit"):
        observer.error("Pipeline aborted by operator.")
        return False, current_topic, classify_res

    mapping = {
        "1": "math", "math": "math",
        "2": "cs", "cs": "cs",
        "3": "ai", "ai": "ai",
        "4": "physics", "physics": "physics",
    }

    if subj_choice in mapping:
        chosen_subject = mapping[subj_choice]
    elif subj_choice in ("5", "other", "custom"):
        try:
            custom_input = Prompt.ask("[bold yellow]Enter custom subject[/bold yellow]").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False, current_topic, classify_res
        chosen_subject = custom_input if custom_input else "math"
    else:
        chosen_subject = subj_choice or "math"

    # Also offer to adjust topic name if needed (e.g. "log" -> "Logarithms")
    try:
        topic_input = Prompt.ask(
            f"[bold yellow]Update topic name[/bold yellow] (press Enter to keep '{current_topic}')",
            default=current_topic,
        ).strip()
    except (EOFError, KeyboardInterrupt):
        topic_input = current_topic

    if topic_input:
        current_topic = topic_input

    # Apply overrides
    old_subject = classify_res.subject
    classify_res.subject = chosen_subject
    classify_res.topic = current_topic
    classify_res.animatable = True
    classify_res.reason = f"[Operator Override] Subject changed from '{old_subject}' to '{chosen_subject}'"

    observer.step(
        "HITL",
        f"Classification updated: Subject=[bold green]{chosen_subject}[/bold green], "
        f"Topic='[bold green]{current_topic}[/bold green]'",
    )

    if workspace:
        workspace.save_classification(classify_res, query=current_text)
        observer.step(
            "WORKSPACE",
            f"Saved updated classification to [bold cyan]{workspace.classification_file.name}[/bold cyan] (JSON format)",
        )

    if run_store:
        run_store.record_run(
            stage="classify_override",
            topic=current_topic,
            model_name="human_override",
            duration=0.0,
            success=True,
            artifacts={"classification": classify_res.model_dump()},
        )

    return True, current_topic, classify_res


async def run_classify_stage(
    text: str,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    *,
    workspace: HitlWorkspace | None = None,
    mock: bool = False,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> VideoClassifyResponse:
    """Execute Stage 1: Pedagogical Animatability Classification."""
    observer.banner("Stage 1: Manim Animatability Classification", "Pydantic AI Classifier Agent")
    observer.step("CLASSIFY", "Evaluating text for mathematical and visual animatability...")

    hooks = create_hitl_local_dev_hooks(observer)
    start_t = time.perf_counter()
    usage = None
    messages = []

    if mock:
        mock_topic = "Fourier Transform"
        mock_subject = "math"
        lower_text = text.lower()
        if "fourier" in lower_text:
            mock_topic = "Fourier Transform"
            mock_subject = "math"
        elif "dijkstra" in lower_text:
            mock_topic = "Dijkstra's Algorithm"
            mock_subject = "cs"
        elif "taylor" in lower_text:
            mock_topic = "Taylor Series Approximation"
            mock_subject = "math"
        elif "binary search" in lower_text:
            mock_topic = "Binary Search"
            mock_subject = "cs"
        elif text.strip():
            mock_topic = text.strip()[:30]

        observer.mock_banner("Stage 1: Manim Animatability Classification", "Pydantic AI Classifier Agent")
        test_model = TestModel(
            custom_output_args={
                "animatable": True,
                "subject": mock_subject,
                "topic": mock_topic,
                "reason": f"[Mock TestModel] Visualizable process for {mock_topic} suitable for Manim animation.",
            }
        )
        agent = Agent(
            model=test_model,
            system_prompt=hitl_agents.CLASSIFIER_SYSTEM_PROMPT,
            name="mock_classifier_agent",
            output_type=VideoClassifyResponse,
        )
        result = await agent.run(text)
        output = result.output
        usage = getattr(result, "usage", None)
        messages = result.all_messages()
        is_mock = True
        is_recovered = False
    else:
        agent = hitl_agents.get_classifier_agent(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            capabilities=[hooks] if hooks else None,
        )
        prompt = f"Please classify the following educational content for Manim animatability:\n\n{text}"
        observer.show_prompt(hitl_agents.CLASSIFIER_SYSTEM_PROMPT, prompt)
        is_mock = False
        is_recovered = False
        captured: list[Any] = []
        try:
            with capture_run_messages() as cm:
                result = await agent.run(prompt)
                output = result.output
                usage = getattr(result, "usage", None)
                messages = result.all_messages() or list(cm)
        except Exception as exc:
            import traceback as _tb
            captured = list(cm) if cm else []
            messages = captured
            recovered = None
            for m in captured:
                for part in getattr(m, "parts", []):
                    content = getattr(part, "content", "")
                    if isinstance(content, str) and "animatable" in content:
                        import re
                        match = re.search(r'\{[^{}]*"animatable"[\s\S]*?\}', content)
                        if match:
                            try:
                                data = json.loads(match.group(0))
                                recovered = VideoClassifyResponse(
                                    animatable=bool(data.get("animatable", True)),
                                    subject=str(data.get("subject", "cs")),
                                    topic=str(data.get("topic", text[:30])),
                                    reason=str(data.get("reason", "Recovered from model output")),
                                )
                            except Exception:
                                pass
                        if recovered:
                            break
                if recovered:
                    break

            if recovered:
                observer.recovery_alarm(
                    stage="classify",
                    exc=exc,
                    method="Regex extraction from raw message parts",
                    traceback_str=_tb.format_exc(),
                )
                output = recovered
                is_recovered = True
            else:
                observer.recovery_alarm(
                    stage="classify",
                    exc=exc,
                    method="classify_text_heuristic() keyword fallback",
                    traceback_str=_tb.format_exc(),
                )
                from app.services.manim_studio import classify_text_heuristic
                output = classify_text_heuristic(text)
                is_recovered = True

    duration = time.perf_counter() - start_t
    observer.show_classification(output, duration=duration, usage=usage, is_mock=is_mock, is_recovered=is_recovered)

    log_file = run_store.record_run(
        stage="classify",
        topic=output.topic,
        model_name="mock:TestModel" if mock else (model_name or "default"),
        duration=duration,
        success=True,
        usage=usage,
        messages=messages,
        artifacts={"classification": output.model_dump()},
    )
    observer.step("SAVE", f"Run recorded to {log_file.name}")

    if workspace:
        workspace.save_classification(output, query=text)
        observer.step("WORKSPACE", f"Saved classification to [bold cyan]{workspace.classification_file.name}[/bold cyan] (JSON format)")

    return output


async def run_compose_stage(
    text: str,
    topic: str,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    *,
    workspace: HitlWorkspace | None = None,
    mock: bool = False,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    subject: str | None = None,
) -> str:
    """Execute Stage 2: scenes.md Visual Plan Composition."""
    observer.banner("Stage 2: scenes.md Visual Plan Composition", "Pydantic AI Composer Agent")
    observer.step("COMPOSE", f"Synthesizing pedagogical animation plan for '{topic}'...")

    hooks = create_hitl_local_dev_hooks(observer)
    start_t = time.perf_counter()
    usage = None
    messages = []

    if mock:
        observer.mock_banner("Stage 2: scenes.md Visual Plan Composition", "Pydantic AI Composer Agent")
        if topic and topic != "Fourier Transform":
            plan_markdown = f"""# Visualizing {topic}

## Overview
- **Topic**: {topic}
- **Hook**: How does {topic} operate intuitively and step-by-step?
- **Target Audience**: Undergraduate STEM learners
- **Estimated Length**: ~30 seconds
- **Key Insight**: Dynamic visual transformations clarify core algorithmic and conceptual steps.

## Narrative Arc
Introduce the initial problem state, animate the step-by-step state transitions, and highlight the final solution.

---

## Scene 1: Initial Setup & Graph/Components
**Duration**: ~10 seconds
**Purpose**: Display the initial state, objects, and layout for {topic}.
### Visual Elements
- Title: Text("{topic}")
- Coordinate layout or diagram nodes.

---

## Scene 2: Algorithmic Execution & Transitions
**Duration**: ~15 seconds
**Purpose**: Animate the core step-by-step updates and logic.
### Visual Elements
- Highlights, node visits, and state changes.

## Color Palette
- Primary: BLUE_C
- Secondary: YELLOW
- Accent: TEAL
"""
        else:
            plan_markdown = MOCK_PLAN
        duration = time.perf_counter() - start_t
    else:
        # Always include manim-composer skill alongside the observer hooks.
        caps = [get_composer_skills()]
        if hooks:
            caps.append(hooks)
        agent = hitl_agents.get_composer_agent(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            capabilities=caps,
        )
        hints_text = f"Subject Domain: {subject}" if subject else None
        deps = hitl_agents.HitlPlanDeps(topic=topic, hints=hints_text, source_text=text)
        subject_line = f"Subject Domain: {subject}\n" if subject else ""
        tier1_context = hitl_agents.get_composer_tier1_preinjected_context()
        user_prompt = (
            f"{tier1_context}\n\n"
            f"Educational Content to visualize:\n{text}\n\n"
            f"Topic: {topic}\n"
            f"{subject_line}\n"
            "Using both the manim-composer and manimce-best-practices skills as your guide, compose a comprehensive "
            "scenes.md visual plan for a 3Blue1Brown-style Manim animation. "
            "Follow the scenes.md format exactly: include Overview, Narrative Arc, "
            "numbered Scenes with Visual Elements / Content / Narration Notes / Technical Notes (explicitly specifying positioning, relative layouts, and coordinate axes via c2p), "
            "Transitions & Flow, Color Palette, and Mathematical Content sections."
        )
        observer.show_prompt(hitl_agents.COMPOSER_SYSTEM_PROMPT, user_prompt)
        with capture_run_messages() as captured:
            result = await agent.run(user_prompt, deps=deps)
            plan_markdown = getattr(result, "output", getattr(result, "data", "")) or ""
            # usage = getattr(result, "usage", None)
            messages = result.all_messages() or captured
        duration = time.perf_counter() - start_t

    observer.show_plan(plan_markdown, topic=topic, duration=duration, usage=usage)

    log_file = run_store.record_run(
        stage="compose",
        topic=topic,
        model_name="mock:TestModel" if mock else (model_name or "default"),
        duration=duration,
        success=bool(plan_markdown),
        usage=usage,
        messages=messages,
        artifacts={"plan": plan_markdown},
    )
    observer.step("SAVE", f"Plan recorded to {log_file.name}")

    if workspace:
        workspace.save_plan(plan_markdown, topic=topic, source_text=text)
        observer.step("WORKSPACE", f"Saved visual plan to [bold cyan]{workspace.plan_md_file.name}[/bold cyan] (Markdown) and [bold cyan]{workspace.plan_json_file.name}[/bold cyan] (JSON format)")

    return plan_markdown


async def run_code_stage(
    plan: str,
    topic: str,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    *,
    workspace: HitlWorkspace | None = None,
    mock: bool = False,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    inject_bug: bool = False,
) -> tuple[str, str]:
    """Execute Stage 3: Manim Python Code Synthesis with Preflight."""
    observer.banner("Stage 3: Manim Python Code Synthesis", "Pydantic AI Coder Agent")
    observer.step("CODE", f"Synthesizing Manim Community Edition code from plan...")

    hooks = create_hitl_local_dev_hooks(observer)
    start_t = time.perf_counter()
    usage = None
    messages = []

    if mock:
        if inject_bug:
            observer.mock_banner("Stage 3: Manim Python Code Synthesis", "Pydantic AI Coder Agent [inject-bug]")
            code = MOCK_BROKEN_CODE_MOBJECT
            detected_scene = "BrokenMobjectScene"
            duration = time.perf_counter() - start_t
        else:
            observer.mock_banner("Stage 3: Manim Python Code Synthesis", "Pydantic AI Coder Agent")
            # Build a realistic mock Manim scene directly from topic + plan.
            # Mock mode tests pipeline plumbing (preflight, LSP, workspace, logging),
            # not the Agent machinery itself (covered by live mode).
            import re as _re
            safe_name = (
                "".join(w.capitalize() for w in _re.sub(r"[^a-zA-Z0-9 ]", "", topic).split())
                or "Generated"
            )
            detected_scene = f"{safe_name}Scene"
            # Derive scene-specific step labels from the plan's ## Scene headings.
            scene_headings = _re.findall(r"## Scene \d+[:\s]+(.+)", plan)
            step_labels = [h.strip()[:40] for h in scene_headings[:3]] or [
                "Initialize State",
                "Animate Core Logic",
                "Highlight Solution",
            ]
            step_items = "\n".join(
                f'            Text("{lbl}", font_size=28, color=TEAL),' for lbl in step_labels
            )
            code = f"""from manim import *

class {detected_scene}(Scene):
    def construct(self):
        title = Text("{topic}", font_size=42, weight=BOLD)
        title.to_edge(UP, buff=0.5)
        underline = Line(title.get_left(), title.get_right(), color=BLUE_C)
        underline.next_to(title, DOWN, buff=0.1)

        self.play(Write(title), Create(underline))
        self.wait(0.4)

        steps = VGroup(
{step_items}
        ).arrange(DOWN, buff=0.35).next_to(underline, DOWN, buff=0.5)

        for step in steps:
            self.play(FadeIn(step, shift=RIGHT * 0.25))
            self.wait(0.35)

        self.wait(1.5)
        self.play(FadeOut(VGroup(title, underline, steps)))
"""
            # Run code through the same extraction/validation path as live output.
            code, detected_scene = hitl_agents.extract_manim_code(
                f"```python\n{code}\n```", default_scene=detected_scene
            )
            duration = time.perf_counter() - start_t
    else:
        # Always wire manimce-best-practices + manim-render skills together with hooks.
        caps = [get_coder_skills()]
        if hooks:
            caps.append(hooks)
        agent = hitl_agents.get_coder_agent(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            capabilities=caps,
        )
        mode_data = workspace.load_mode_selection() if workspace else None
        mode = (mode_data or {}).get("mode", "animation")
        saved_class = workspace.load_classification() if workspace else None
        needs_3d = bool((saved_class or {}).get("needs_3d", False))

        if mode == "slide":
            tier1_context = hitl_agents.get_slide_tier1_context()
            mode_guideline = (
                "MODE: SLIDE MODE. Structure into distinct slides with VGroups, "
                "FadeOut transitions, and clear pauses (self.wait(2.0-3.0)). Do NOT use continuous updaters."
            )
        elif mode == "scivis":
            libs = (mode_data or {}).get("scivis_libraries", [])
            tier1_context = hitl_agents.get_scivis_tier1_context(libraries=libs, needs_3d=needs_3d)
            mode_guideline = (
                "MODE: SCIVIS MODE. Implement a standalone get_data() function before the Scene class, "
                "call it in construct(), and map scientific data to Manim primitives with graceful fallbacks."
            )
        elif mode == "marp":
            tier1_context = hitl_agents.get_marp_tier1_context()
            mode_guideline = (
                "MODE: MARP MODE (Declarative Slide Presentation). Follow the 6-archetype layout vocabulary strictly: "
                "title, bullets, two-col, code-focus, math-focus, quote. Group each slide in a VGroup and use clean FadeOut transitions."
            )
        else:
            tier1_context = hitl_agents.get_animation_tier1_context(needs_3d=needs_3d)
            mode_guideline = (
                "MODE: ANIMATION MODE. Emphasize fluid motion, relative positioning, updaters, and seamless transforms."
            )

        deps = hitl_agents.HitlCoderDeps(plan=plan, knowledge_text=topic, mode=mode)
        user_prompt = (
            f"Topic: {topic}\n\n"
            f"Mode: {mode.upper()}\n\n"
            f"Approved scenes.md Visual Plan:\n{plan}\n\n"
            f"{tier1_context}\n\n"
            f"{mode_guideline}\n\n"
            "Following the pre-injected manimce-best-practices Tier 1 rules strictly, synthesize a complete, "
            "production-quality Manim Community Edition Python scene that faithfully implements "
            "every scene described in the plan above. "
            "NEVER use raw coordinate literals or manual float shifts. Use relative layouts (.next_to, .arrange, .to_edge) "
            "or axes.c2p(). "
            "Name the Scene class after the topic (e.g. class DijkstrasAlgorithmScene(Scene):). "
            "Return only the executable Python code block inside ```python ... ```."
        )
        observer.show_prompt(hitl_agents.CODER_SYSTEM_PROMPT, user_prompt)
        with capture_run_messages() as captured:
            result = await agent.run(
                user_prompt,
                deps=deps,
                model_settings=ModelSettings(max_tokens=hitl_agents.HITL_MAX_TOKENS),
            )
            raw_response = getattr(result, "output", getattr(result, "data", "")) or ""
            usage = getattr(result, "usage", None)
            messages = result.all_messages() or captured
        code, detected_scene = hitl_agents.extract_manim_code(raw_response, default_scene="GeneratedScene")
        duration = time.perf_counter() - start_t

        if inject_bug:
            code = MOCK_BROKEN_CODE_MOBJECT
            detected_scene = "BrokenMobjectScene"

    observer.show_code(code, scene_name=detected_scene, duration=duration, usage=usage)

    # Deterministic formatting & string repairs pass
    repair = repair_manim_code(code)

    # Stage 4: Pyright LSP & LaTeX Diagnostics (Primary Quality Gate)
    observer.banner("Stage 4: Pyright LSP Diagnostics & Code Validation", "Authoritative Type, Member & Syntax Guardrails")
    lsp_report = run_pyright_lsp(repair.code, is_code=True)
    
    from app.services.latex_validator import run_latex_diagnostics
    from app.services.positioning_linter import lint_manim_positioning
    from app.services.lsp_service import LspDiagnostic
    for ld in run_latex_diagnostics(repair.code):
        lsp_report.diagnostics.append(
            LspDiagnostic(
                file="scene.py",
                severity="error",
                message=f"LaTeX Error: {ld.message}\n  In string: '{ld.tex_string}'",
                line=ld.line,
                character=ld.column,
                rule="reportLaTeXCompilationError",
            )
        )
    pos_report = lint_manim_positioning(repair.code)
    for issue in pos_report.issues:
        lsp_report.diagnostics.append(
            LspDiagnostic(
                file="scene.py",
                severity="error" if issue.severity == "error" else "warning",
                message=f"Positioning Lint: {issue.message}\n  Suggestion: {issue.suggestion}",
                line=issue.line,
                character=issue.col,
                rule="reportPositioningSmell",
            )
        )
    
    observer.show_lsp(lsp_report)

    if repair.changes:
        observer.step("FORMAT", f"Applied {len(repair.changes)} deterministic formatting/LaTeX improvement(s)")

    # Save generated source to disk for immediate access
    scene_dir = Path(__file__).parent / ".dev_logs" / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)
    saved_scene_path = scene_dir / f"{detected_scene}.py"
    saved_scene_path.write_text(repair.code, encoding="utf-8")
    observer.step("CODE", f"Saved generated source to [bold cyan]{saved_scene_path.resolve()}[/bold cyan]")

    is_clean = bool(lsp_report and not lsp_report.has_errors)
    log_file = run_store.record_run(
        stage="code",
        topic=topic,
        model_name="mock:TestModel" if mock else (model_name or "default"),
        duration=duration,
        success=is_clean,
        usage=usage,
        messages=messages,
        preflight=None,
        repair=repair,
        artifacts={
            "code": code,
            "repaired_code": repair.code,
            "scene_name": detected_scene,
            "file_path": str(saved_scene_path.resolve()),
            "lsp_diagnostics": [d.__dict__ for d in lsp_report.diagnostics] if lsp_report else [],
        },
    )
    observer.step("SAVE", f"Code run recorded to {log_file.name}")

    if workspace:
        workspace.save_code(
            repair.code,
            scene_name=detected_scene,
            topic=topic,
            preflight=None,
            repair=repair,
            lsp_report=lsp_report,
        )
        observer.step("WORKSPACE", f"Saved Manim scene to [bold cyan]{workspace.scene_file.name}[/bold cyan] (Python) and [bold cyan]{workspace.code_json_file.name}[/bold cyan] (JSON format)")

    return repair.code, detected_scene


async def run_repair_stage(
    code: str,
    error_traceback: str,
    scene_name: str,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    *,
    workspace: HitlWorkspace | None = None,
    mock: bool = False,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str]:
    """Execute Stage 5: In-Place Self-Correcting Code Repair."""
    observer.banner("Stage 5: Self-Correcting Code Repair", "Pydantic AI Repair Agent + Preflight Loop")
    observer.step("REPAIR", f"Classifying traceback and preparing targeted repair...")

    classified = classify_error(error_traceback)
    guidance = get_repair_guidance(classified)
    observer.step("DIAG", f"Category: [bold red]{classified.category.value}[/bold red]", classified.user_message)
    observer.console.print(f"[dim]Guidance: {guidance}[/dim]\n")

    start_t = time.perf_counter()
    original_repair = repair_manim_code(code)
    current_code = original_repair.code

    # Pyright LSP Diagnostics for deep attribute & member checking
    lsp_report = run_pyright_lsp(current_code, is_code=True)
    observer.show_lsp(lsp_report)

    diagnostic_bundle = {
        "stage": "repair",
        "category": classified.category.value,
        "guidance": guidance,
        "runtime_or_compiler": error_traceback[-4000:],
        "static_findings": [],
        "lsp_findings": lsp_report.format_feedback() if lsp_report else "",
        "deterministic_repairs_already_applied": list(original_repair.changes),
    }

    prompt = f"""Repair this existing Manim Community Edition source in place.
Diagnostic bundle:
{json.dumps(diagnostic_bundle, indent=2)}

Targeted repair guidance:
{guidance}

Current source:
```python
{current_code}
```
"""
    deps = hitl_agents.HitlRepairDeps(
        error=error_traceback,
        current_code=current_code,
        scene_name=scene_name,
        classified_error=classified,
        diagnostic_bundle=diagnostic_bundle,
    )

    repaired_code = current_code
    detected_scene = scene_name
    usage = None
    messages = []

    if mock:
        observer.mock_banner("Stage 5: Self-Correcting Code Repair", "Pydantic AI Repair Agent + Preflight Loop")
        # Simulate successful repair that replaces bad indexing with safe get_part_by_tex or separate MathTex
        repaired_code = MOCK_VALID_CODE
        detected_scene = "FourierTransformScene"
        duration = time.perf_counter() - start_t
    else:
        hooks = create_hitl_local_dev_hooks(observer)
        # Wire manimce-best-practices + manim-render skills for the repair agent.
        repair_caps = [get_repair_skills()]
        if hooks:
            repair_caps.append(hooks)
        agent = hitl_agents.get_repair_agent(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            capabilities=repair_caps,
        )
        observer.show_prompt(hitl_agents.REPAIR_SYSTEM_PROMPT, prompt)
        with capture_run_messages() as captured:
            repaired_code, detected_scene = await hitl_agents.run_repair_with_self_correction(
                agent=agent,
                prompt=prompt,
                deps=deps,
                max_attempts=2,
                timeout=90.0,
            )
            messages = captured
        duration = time.perf_counter() - start_t

    # Show code diff
    observer.show_code_diff(code, repaired_code, title="Repaired Code Diff vs Original")

    # Post-repair validation with Pyright LSP
    final_repair = repair_manim_code(repaired_code)
    final_lsp = run_pyright_lsp(final_repair.code, is_code=True)
    observer.show_lsp(final_lsp)

    log_file = run_store.record_run(
        stage="repair",
        topic=scene_name,
        model_name="mock:TestModel" if mock else (model_name or "default"),
        duration=duration,
        success=bool(final_lsp and not final_lsp.has_errors),
        usage=usage,
        messages=messages,
        preflight=None,
        repair=final_repair,
        artifacts={
            "original_code": code,
            "repaired_code": final_repair.code,
            "error": error_traceback,
            "lsp_diagnostics": [d.__dict__ for d in final_lsp.diagnostics] if final_lsp else [],
        },
    )
    observer.step("SAVE", f"Repair run recorded to {log_file.name}")

    if workspace:
        workspace.save_repair(
            repaired_code=final_repair.code,
            scene_name=detected_scene,
            error=error_traceback,
            category=classified.category.value,
            changes=list(original_repair.changes) + list(final_repair.changes),
        )
        observer.step("WORKSPACE", f"Updated [bold cyan]{workspace.scene_file.name}[/bold cyan] (Python) and saved [bold cyan]{workspace.repair_file.name}[/bold cyan] (JSON format)")

    return final_repair.code, detected_scene


# ── Standalone Preflight / LSP Inspector ──────────────────────────────────────

def run_preflight_inspector(
    file_path: str | None,
    inline_code: str | None,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    workspace: HitlWorkspace | None = None,
) -> None:
    """Inspect and test any Python file or inline string against Pyright LSP rules."""
    observer.banner("Manim Code LSP & Deterministic Inspector", "Pyright Type Checking & Formatting Analysis")

    code = ""
    if file_path:
        p = Path(file_path)
        if not p.exists():
            observer.error(f"File not found: {file_path}")
            return
        code = p.read_text(encoding="utf-8")
        observer.step("LOAD", f"Loaded source from [underline]{file_path}[/underline]")
    elif inline_code:
        code = inline_code
    elif workspace and workspace.scene_file.exists():
        code = workspace.scene_file.read_text(encoding="utf-8")
        file_path = str(workspace.scene_file)
        observer.step("WORKSPACE", f"Loaded source from [bold cyan]{workspace.scene_file.name}[/bold cyan] (Python format)")
    else:
        observer.error("No file or code provided. Use --file, provide inline code, or run in a workspace.")
        return

    repair = repair_manim_code(code)

    if repair.changes:
        observer.show_code_diff(code, repair.code, title="Deterministic Formatting Changes Applied")

    # Pyright LSP & LaTeX Diagnostics
    lsp_report = run_pyright_lsp(repair.code, is_code=True)
    
    from app.services.latex_validator import run_latex_diagnostics
    from app.services.lsp_service import LspDiagnostic
    for ld in run_latex_diagnostics(repair.code):
        lsp_report.diagnostics.append(
            LspDiagnostic(
                file="scene.py",
                severity="error",
                message=f"LaTeX Error: {ld.message}\n  In string: '{ld.tex_string}'",
                line=ld.line,
                character=ld.column,
                rule="reportLaTeXCompilationError",
            )
        )
        
    observer.show_lsp(lsp_report)

    if workspace:
        workspace.save_preflight(None, repair, lsp_report)
        if repair.changes:
            workspace.scene_file.write_text(repair.code, encoding="utf-8")
            observer.step("WORKSPACE", f"Updated [bold cyan]{workspace.scene_file.name}[/bold cyan] with formatting fixes and saved [bold cyan]{workspace.preflight_file.name}[/bold cyan] (JSON format)")

    run_store.record_run(
        stage="preflight",
        topic=file_path or "inline_code",
        model_name="pyright_lsp",
        duration=lsp_report.time_taken_sec if lsp_report else 0.01,
        success=bool(lsp_report and not lsp_report.has_errors),
        preflight=None,
        repair=repair,
        artifacts={"original_code": code, "repaired_code": repair.code, "lsp_feedback": lsp_report.format_feedback() if lsp_report else ""},
    )


def run_lsp_inspector(
    file_path: str | None,
    inline_code: str | None,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
) -> None:
    """Inspect and test any Python file or inline string using Pyright LSP server."""
    observer.banner("Manim Code Pyright LSP Inspector", "Type Checking & Member Diagnostics")

    code = ""
    if file_path:
        p = Path(file_path)
        if not p.exists():
            observer.error(f"File not found: {file_path}")
            return
        code = p.read_text(encoding="utf-8")
        observer.step("LOAD", f"Loaded source from [underline]{file_path}[/underline]")
        report = run_pyright_lsp(p)
    elif inline_code:
        code = inline_code
        report = run_pyright_lsp(inline_code, is_code=True)
    else:
        observer.error("No file or code provided. Use --file or provide inline code.")
        return

    observer.show_lsp(report)

    run_store.record_run(
        stage="lsp",
        topic=file_path or "inline_code",
        model_name="pyright_lsp",
        duration=report.time_taken_sec,
        success=report.success and not report.has_errors,
        artifacts={"code": code, "feedback": report.format_feedback(), "error_count": report.error_count},
    )


# ── Optional Manim Render Test ────────────────────────────────────────────────

def run_local_render_check(
    code: str,
    scene_name: str,
    observer: HitlTerminalObserver,
    workspace: HitlWorkspace | None = None,
) -> Path | None:
    """Optionally run 'manim -ql' on the generated code and preserve the output video."""
    import subprocess
    import shutil

    observer.banner("Optional Local Render Verification", "Running `manim -ql` locally")
    observer.step("RENDER", f"Compiling Scene '{scene_name}' at low quality...")

    if workspace:
        render_dir = workspace.workspace_dir
        scene_file = workspace.scene_file
        scene_file.write_text(code, encoding="utf-8")
    else:
        render_dir = Path(__file__).parent / ".dev_logs" / "renders" / scene_name
        render_dir.mkdir(parents=True, exist_ok=True)
        scene_file = render_dir / f"{scene_name}.py"
        scene_file.write_text(code, encoding="utf-8")

    # Check for direct 'manim' or 'uv'
    if shutil.which("manim"):
        cmd = ["manim", "-ql", str(scene_file), scene_name]
    elif shutil.which("uv"):
        cmd = ["uv", "run", "manim", "-ql", str(scene_file), scene_name]
    else:
        cmd = ["manim", "-ql", str(scene_file), scene_name]

    try:
        start_t = time.perf_counter()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(render_dir),
        )
        elapsed = time.perf_counter() - start_t
        if proc.returncode == 0:
            observer.success(f"Render completed cleanly in {elapsed:.2f}s!")
            # Find the rendered video
            video_candidates = list(render_dir.glob(f"**/videos/**/{scene_name}.mp4")) or list(render_dir.glob("**/*.mp4"))
            if video_candidates:
                target_video = video_candidates[0].resolve()
                observer.step("VIDEO", f"Compiled video: [bold green]{target_video}[/bold green]")
                return target_video
            else:
                observer.step("OUTPUT", f"Render directory: [bold green]{render_dir.resolve()}[/bold green]")
                return render_dir
        else:
            observer.error(f"Render failed with return code {proc.returncode}")
            observer.console.print(f"[red]{proc.stderr[-1000:]}[/red]")
            return None
    except FileNotFoundError:
        observer.warning("`manim` executable not found. Make sure Manim is installed or render via Docker.")
        return None
    except subprocess.TimeoutExpired:
        observer.error("Manim render timed out after 180s.")
        return None
    except Exception as exc:
        observer.error(f"Render verification error: {exc}")
        return None


# ── Inspect Last Run ──────────────────────────────────────────────────────────

def inspect_last_run(
    run_store: HitlRunStore,
    observer: HitlTerminalObserver,
    workspace: HitlWorkspace | None = None,
) -> None:
    """Display summary and diagnostics from the most recent run log."""
    last_run = run_store.get_last_run()
    if not last_run:
        observer.warning(f"No run logs found in {run_store.log_dir}")
        if workspace:
            observer.show_workspace_status(workspace)
        return

    observer.banner(f"Last Run Inspection: {last_run.get('stage', 'unknown').upper()}", f"Run ID: {last_run.get('run_id')}")

    metadata_table = Table(box=SIMPLE, show_header=False)
    metadata_table.add_column("Key", style="bold cyan")
    metadata_table.add_column("Value")

    metadata_table.add_row("Timestamp", str(last_run.get("timestamp")))
    metadata_table.add_row("Stage", str(last_run.get("stage")))
    metadata_table.add_row("Topic", str(last_run.get("topic")))
    metadata_table.add_row("Model", str(last_run.get("model")))
    metadata_table.add_row("Duration", f"{last_run.get('duration_seconds', 0)}s")
    metadata_table.add_row("Success", "[bold green]YES[/bold green]" if last_run.get("success") else "[bold red]NO[/bold red]")

    observer.console.print(Panel(metadata_table, title="Run Metadata", box=ROUNDED))

    # Preflight issues if any
    preflight = last_run.get("preflight")
    if preflight and not preflight.get("valid"):
        errors = preflight.get("errors", [])
        observer.error(f"Preflight had {len(errors)} error(s):")
        for err in errors:
            observer.console.print(f"  • [red]Line {err.get('line')}[/red]: {err.get('message')}")

    # Messages count
    messages = last_run.get("messages", [])
    observer.step("LOG", f"Recorded {len(messages)} Pydantic AI messages in conversation history")

    if workspace:
        observer.show_workspace_status(workspace)


# ── CLI Entrypoint ────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Frictionless Local Dev & Test Runner for Pydantic AI HITL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("topic", nargs="?", default=None, help="Topic or educational text to process (if omitted, loads from workspace)")
    parser.add_argument(
        "-s", "--stage",
        choices=["all", "classify", "compose", "code", "preflight", "repair", "lsp"],
        default="all",
        help="Pipeline stage to run (default: all)",
    )
    parser.add_argument(
        "-d", "--dir", "--workspace",
        dest="workspace_dir",
        default=None,
        help="Directory for structural JSON and Python artifacts (default: hitl_workspace/)",
    )
    parser.add_argument("--mock", action="store_true", help="Run with Pydantic AI TestModel (offline, 0 API tokens)")
    parser.add_argument(
        "--no-hitl-approval",
        action="store_true",
        default=False,
        help="Skip human approval gates between stages (CI/batch mode)",
    )
    parser.add_argument(
        "-m", "--model",
        default=os.getenv("AI_MODEL") or os.getenv("AOS_OPENAI_MODEL") or "nvidia/nemotron-3-ultra-550b-a55b:free",
        help="LLM model override (default: nvidia/nemotron-3-ultra-550b-a55b:free)",
    )
    parser.add_argument(
        "-b", "--base-url",
        default=os.getenv("AOS_OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        help="LLM base URL / endpoint (default: https://openrouter.ai/api/v1)",
    )
    parser.add_argument(
        "-k", "--api-key",
        default=os.getenv("OPENROUTER_API_KEY", "") or os.getenv("AOS_OPENAI_API_KEY", ""),
        help="API key for OpenRouter or custom endpoint",
    )
    parser.add_argument("-f", "--file", default=None, help="Python source file for preflight, repair, or lsp stage")
    parser.add_argument("-e", "--error", default=None, help="Traceback or compiler error for repair stage")
    parser.add_argument("--inject-mobject-bug", action="store_true", help="Inject intentional mobject index error to test repair agent")
    parser.add_argument("--render", action="store_true", help="Verify scene compilation with local `manim -ql`")
    parser.add_argument("--inspect-last", action="store_true", help="Inspect details of the most recent local run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show full prompts and verbose conversation traces")
    parser.add_argument("--web", action="store_true", help="Launch Pydantic AI Web Chat UI in browser")
    parser.add_argument("--host", default="127.0.0.1", help="Host for Web Chat UI (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7932, help="Port for Web Chat UI (default: 7932)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")
    parser.add_argument("--log-dir", default=None, help="Custom local log storage directory")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()

    # 0. Check for Web Chat UI mode
    if args.web:
        from dev_hitl_web import run_web_server
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
        )
        return

    # 1. Disable Logfire remote export for local development
    disable_logfire_remote()

    run_store = HitlRunStore(log_dir=args.log_dir)
    workspace = HitlWorkspace(workspace_dir=args.workspace_dir)
    observer = HitlTerminalObserver(verbose=args.verbose, mock_mode=args.mock)

    if args.inspect_last:
        inspect_last_run(run_store, observer, workspace=workspace)
        return

    # Check for LSP inspection stage on file or text
    if args.stage == "lsp":
        run_lsp_inspector(args.file, None if args.file else args.topic, observer, run_store)
        return

    # Check for preflight stage on file or text
    if args.stage == "preflight":
        run_preflight_inspector(args.file, None if args.file else args.topic, observer, run_store, workspace=workspace)
        return

    start_total_t = time.perf_counter()
    observer.banner(
        "AOS HITL Local Development Runner",
        f"Mode: {'\u26a0  MOCK (Pydantic AI TestModel)  \u26a0' if args.mock else 'LIVE LLM'}  "
        f"|  Stage: {args.stage.upper()}  |  Workspace: {workspace.workspace_dir.name}",
    ) if not args.mock else observer.mock_banner(
        "AOS HITL Local Development Runner",
        f"Stage: {args.stage.upper()}  |  Workspace: {workspace.workspace_dir.name}",
    )
    observer.step("WORKSPACE", f"Active directory: [bold cyan]{workspace.workspace_dir}[/bold cyan]")

    try:
        # Check API key if not in mock mode
        if not args.mock:
            try:
                hitl_agents._resolve_llm_config(
                    api_key=args.api_key,
                    base_url=args.base_url,
                    model_name=args.model,
                )
            except ValueError as exc:
                observer.error(str(exc))
                observer.console.print(
                    "\n[bold yellow]Tip:[/bold yellow] To test offline without an API key, add the [bold cyan]--mock[/bold cyan] flag:\n"
                    f"  [green]uv run python dev_hitl.py --mock \"{args.topic or 'Fourier Transform'}\"[/green]\n"
                )
                return

        # STAGE: CLASSIFY
        if args.stage in ("classify", "all"):
            text_to_classify = args.topic
            if not text_to_classify:
                inp = workspace.load_input()
                if inp and inp.get("text"):
                    text_to_classify = inp["text"]
                    observer.step("WORKSPACE", f"Loaded input query from [bold cyan]{workspace.input_file.name}[/bold cyan] (JSON format)")
                else:
                    text_to_classify = "Fourier Transform"

            workspace.save_input(text_to_classify)

            classify_res = await run_classify_stage(
                text_to_classify,
                observer,
                run_store,
                workspace=workspace,
                mock=args.mock,
                model_name=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
            )
            current_topic = classify_res.topic or text_to_classify
            current_text = text_to_classify
            # ── HITL Checkpoint 1: Approve classification ──
            if args.stage in ("classify", "all"):
                proceed, current_topic, classify_res = hitl_classify_checkpoint(
                    observer,
                    classify_res,
                    current_topic,
                    current_text,
                    workspace=workspace,
                    run_store=run_store,
                    auto_approve=args.no_hitl_approval,
                )
                if not proceed:
                    return

            if not classify_res.animatable and args.stage == "all":
                observer.warning("Content classified as non-animatable. Halting pipeline.")
                return
        else:
            class_data = workspace.load_classification()
            if args.topic:
                current_topic = args.topic
                current_text = args.topic
            elif class_data:
                current_topic = class_data.get("topic") or "Fourier Transform"
                current_text = class_data.get("query") or current_topic
                observer.step("WORKSPACE", f"Loaded topic '[bold green]{current_topic}[/bold green]' from [bold cyan]{workspace.classification_file.name}[/bold cyan] (JSON format)")
            else:
                inp = workspace.load_input()
                if inp:
                    current_topic = inp.get("topic") or inp.get("text", "Fourier Transform")[:30]
                    current_text = inp.get("text") or current_topic
                else:
                    current_topic = "Fourier Transform"
                    current_text = MOCK_TEXT

        # STAGE: COMPOSE
        if args.stage in ("compose", "all"):
            subject_to_pass = None
            if "classify_res" in locals() and classify_res:
                subject_to_pass = classify_res.subject
            else:
                class_data = workspace.load_classification()
                if class_data:
                    subject_to_pass = class_data.get("subject")

            plan = await run_compose_stage(
                current_text,
                current_topic,
                observer,
                run_store,
                workspace=workspace,
                mock=args.mock,
                model_name=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
                subject=subject_to_pass,
            )
            # ── HITL Checkpoint 2: Approve visual plan ──
            import re as _re
            scene_count = len(_re.findall(r"## Scene \d+", plan))
            summary = f"scenes.md plan generated  |  Detected scenes: {scene_count}  |  Topic: [bold]{current_topic}[/bold]"
            if not hitl_approve(observer, "COMPOSE", summary, auto_approve=args.no_hitl_approval):
                return
        else:
            loaded_plan, loaded_topic = workspace.load_plan()
            if loaded_plan:
                plan = loaded_plan
                if loaded_topic and not args.topic:
                    current_topic = loaded_topic
                observer.step("WORKSPACE", f"Loaded visual plan from [bold cyan]{workspace.plan_md_file.name}[/bold cyan] (Markdown format)")
            else:
                plan = MOCK_PLAN

        # STAGE: CODE
        if args.stage in ("code", "all"):
            code, scene_name = await run_code_stage(
                plan,
                current_topic,
                observer,
                run_store,
                workspace=workspace,
                mock=args.mock,
                model_name=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
                inject_bug=args.inject_mobject_bug,
            )
        elif args.file:
            code = Path(args.file).read_text(encoding="utf-8")
            scene_name = "CustomScene"
        else:
            loaded_code, loaded_scene = workspace.load_code()
            if loaded_code and not args.inject_mobject_bug:
                code = loaded_code
                scene_name = loaded_scene or "GeneratedScene"
                observer.step("WORKSPACE", f"Loaded existing scene from [bold cyan]{workspace.scene_file.name}[/bold cyan] (Python format)")
            else:
                code = MOCK_BROKEN_CODE_MOBJECT if args.inject_mobject_bug else MOCK_VALID_CODE
                scene_name = "BrokenMobjectScene" if args.inject_mobject_bug else "FourierTransformScene"

        # STAGE: REPAIR (if explicitly requested, or if preflight failed during 'all')
        if args.stage == "repair" or (args.stage == "all" and args.inject_mobject_bug):
            sample_err = args.error or workspace.load_error() or (
                "IndexError: list index out of range\n"
                "  File 'scene.py', line 7, in construct\n"
                "    square = formula[5]\n"
                "IndexError: list index out of range"
            )
            repaired_code, scene_name = await run_repair_stage(
                code,
                sample_err,
                scene_name,
                observer,
                run_store,
                workspace=workspace,
                mock=args.mock,
                model_name=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
            )
            code = repaired_code

        # Optional local render
        if args.render:
            run_local_render_check(code, scene_name, observer, workspace=workspace)

        total_elapsed = time.perf_counter() - start_total_t
        observer.show_run_summary(
            stage=args.stage,
            status="success",
            duration=total_elapsed,
            usage={},
            log_path=run_store.last_run_file,
        )
        observer.show_workspace_status(workspace)

    except KeyboardInterrupt:
        observer.warning("Run aborted by user (KeyboardInterrupt).")
    except Exception as exc:
        import traceback as _tb
        tb_str = _tb.format_exc()
        observer.error(f"Pipeline failed: {type(exc).__name__}: {exc}")
        # Always print full traceback — do not hide failures behind --verbose.
        observer.console.print(f"[dim red]{tb_str}[/dim red]")
        if observer.recovered_stages:
            observer.warning(
                f"Note: the following stages used fallback/recovery data (NOT real LLM output): "
                + ", ".join(observer.recovered_stages)
            )


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

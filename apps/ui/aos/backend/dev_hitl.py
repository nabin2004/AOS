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
from rich.box import ROUNDED, SIMPLE
from rich.panel import Panel
from rich.table import Table

import app.agents.hitl_agents as hitl_agents
from app.agents.error_classifier import classify_error, get_repair_guidance
from app.core.local_logging import (
    HitlRunStore,
    HitlTerminalObserver,
    create_hitl_local_dev_hooks,
    disable_logfire_remote,
)
from app.schemas.video_generation import VideoClassifyResponse
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


# ── Stage Runners ─────────────────────────────────────────────────────────────

async def run_classify_stage(
    text: str,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    *,
    mock: bool = False,
    model_name: str | None = None,
) -> VideoClassifyResponse:
    """Execute Stage 1: Pedagogical Animatability Classification."""
    observer.banner("Stage 1: Manim Animatability Classification", "Pydantic AI Classifier Agent")
    observer.step("CLASSIFY", "Evaluating text for mathematical and visual animatability...")

    hooks = create_hitl_local_dev_hooks(observer)
    start_t = time.perf_counter()
    usage = None
    messages = []

    if mock:
        test_model = TestModel(
            custom_output_args={
                "animatable": True,
                "subject": "math",
                "topic": "Fourier Transform",
                "reason": "[Mock TestModel] Decomposes continuous signals into sinusoidal harmonics suitable for Manim animation.",
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
    else:
        agent = hitl_agents.get_classifier_agent(model_name=model_name, capabilities=[hooks] if hooks else None)
        prompt = f"Please classify the following educational content for Manim animatability:\n\n{text}"
        observer.show_prompt(hitl_agents.CLASSIFIER_SYSTEM_PROMPT, prompt)
        with capture_run_messages() as captured:
            result = await agent.run(prompt)
            output = result.output
            usage = getattr(result, "usage", None)
            messages = result.all_messages() or captured

    duration = time.perf_counter() - start_t
    observer.show_classification(output, duration=duration, usage=usage)

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
    return output


async def run_compose_stage(
    text: str,
    topic: str,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    *,
    mock: bool = False,
    model_name: str | None = None,
) -> str:
    """Execute Stage 2: scenes.md Visual Plan Composition."""
    observer.banner("Stage 2: scenes.md Visual Plan Composition", "Pydantic AI Composer Agent")
    observer.step("COMPOSE", f"Synthesizing pedagogical animation plan for '{topic}'...")

    hooks = create_hitl_local_dev_hooks(observer)
    start_t = time.perf_counter()
    usage = None
    messages = []

    if mock:
        plan_markdown = MOCK_PLAN
        duration = time.perf_counter() - start_t
    else:
        agent = hitl_agents.get_composer_agent(model_name=model_name, capabilities=[hooks] if hooks else None)
        deps = hitl_agents.HitlPlanDeps(topic=topic, source_text=text)
        user_prompt = f"Educational Content:\n{text}\n\nPlease construct a comprehensive scenes.md visual plan for Manim focusing on topic '{topic}'."
        observer.show_prompt(hitl_agents.COMPOSER_SYSTEM_PROMPT, user_prompt)
        with capture_run_messages() as captured:
            result = await agent.run(user_prompt, deps=deps)
            plan_markdown = getattr(result, "output", getattr(result, "data", "")) or ""
            usage = getattr(result, "usage", None)
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
    return plan_markdown


async def run_code_stage(
    plan: str,
    topic: str,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    *,
    mock: bool = False,
    model_name: str | None = None,
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
        code = MOCK_BROKEN_CODE_MOBJECT if inject_bug else MOCK_VALID_CODE
        detected_scene = "BrokenMobjectScene" if inject_bug else "FourierTransformScene"
        duration = time.perf_counter() - start_t
    else:
        agent = hitl_agents.get_coder_agent(model_name=model_name, capabilities=[hooks] if hooks else None)
        deps = hitl_agents.HitlCoderDeps(plan=plan, knowledge_text=topic)
        user_prompt = f"Approved Visual Plan (scenes.md):\n{plan}\n\nSynthesize a complete, elegant Manim Community scene implementing this plan."
        observer.show_prompt(hitl_agents.CODER_SYSTEM_PROMPT, user_prompt)
        with capture_run_messages() as captured:
            result = await agent.run(user_prompt, deps=deps)
            raw_response = getattr(result, "output", getattr(result, "data", "")) or ""
            usage = getattr(result, "usage", None)
            messages = result.all_messages() or captured
        code, detected_scene = hitl_agents.extract_manim_code(raw_response, default_scene="GeneratedScene")
        duration = time.perf_counter() - start_t

        if inject_bug:
            code = MOCK_BROKEN_CODE_MOBJECT
            detected_scene = "BrokenMobjectScene"

    observer.show_code(code, scene_name=detected_scene, duration=duration, usage=usage)

    # Preflight Check
    observer.banner("Stage 4: Static AST Validation & Preflight", "Deterministic Code Quality Guardrails")
    repair = repair_manim_code(code)
    preflight = preflight_manim_code(repair.code)
    observer.show_preflight(preflight, repair)

    log_file = run_store.record_run(
        stage="code",
        topic=topic,
        model_name="mock:TestModel" if mock else (model_name or "default"),
        duration=duration,
        success=preflight.valid,
        usage=usage,
        messages=messages,
        preflight=preflight,
        repair=repair,
        artifacts={"code": code, "repaired_code": repair.code, "scene_name": detected_scene},
    )
    observer.step("SAVE", f"Code run recorded to {log_file.name}")
    return repair.code, detected_scene


async def run_repair_stage(
    code: str,
    error_traceback: str,
    scene_name: str,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
    *,
    mock: bool = False,
    model_name: str | None = None,
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
    preflight = preflight_manim_code(current_code)

    diagnostic_bundle = {
        "stage": "repair",
        "category": classified.category.value,
        "guidance": guidance,
        "runtime_or_compiler": error_traceback[-4000:],
        "static_findings": list(preflight.errors),
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
        # Simulate successful repair that replaces bad indexing with safe get_part_by_tex or separate MathTex
        repaired_code = MOCK_VALID_CODE
        detected_scene = "FourierTransformScene"
        duration = time.perf_counter() - start_t
    else:
        hooks = create_hitl_local_dev_hooks(observer)
        agent = hitl_agents.get_repair_agent(model_name=model_name, capabilities=[hooks] if hooks else None)
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

    # Post-repair preflight
    final_repair = repair_manim_code(repaired_code)
    final_preflight = preflight_manim_code(final_repair.code)
    observer.show_preflight(final_preflight, final_repair)

    log_file = run_store.record_run(
        stage="repair",
        topic=scene_name,
        model_name="mock:TestModel" if mock else (model_name or "default"),
        duration=duration,
        success=final_preflight.valid,
        usage=usage,
        messages=messages,
        preflight=final_preflight,
        repair=final_repair,
        artifacts={"original_code": code, "repaired_code": final_repair.code, "error": error_traceback},
    )
    observer.step("SAVE", f"Repair run recorded to {log_file.name}")
    return final_repair.code, detected_scene


# ── Standalone Preflight Inspector ────────────────────────────────────────────

def run_preflight_inspector(
    file_path: str | None,
    inline_code: str | None,
    observer: HitlTerminalObserver,
    run_store: HitlRunStore,
) -> None:
    """Inspect and test any Python file or inline string against preflight rules."""
    observer.banner("Manim Code Preflight & Deterministic AST Fixer", "Local Static Analysis")

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
    else:
        observer.error("No file or code provided. Use --file or provide inline code.")
        return

    repair = repair_manim_code(code)
    preflight = preflight_manim_code(repair.code)

    if repair.changes:
        observer.show_code_diff(code, repair.code, title="Deterministic AST Changes Applied")

    observer.show_preflight(preflight, repair)

    run_store.record_run(
        stage="preflight",
        topic=file_path or "inline_code",
        model_name="deterministic_ast",
        duration=0.01,
        success=preflight.valid,
        preflight=preflight,
        repair=repair,
        artifacts={"original_code": code, "repaired_code": repair.code},
    )


# ── Optional Manim Render Test ────────────────────────────────────────────────

def run_local_render_check(
    code: str,
    scene_name: str,
    observer: HitlTerminalObserver,
) -> None:
    """Optionally run 'manim -ql' on the generated code using local Manim CLI."""
    import subprocess
    import tempfile

    observer.banner("Optional Local Render Verification", "Running `manim -ql` locally")
    observer.step("RENDER", f"Compiling Scene '{scene_name}' at low quality...")

    with tempfile.TemporaryDirectory() as tmpdir:
        scene_file = Path(tmpdir) / "scene.py"
        scene_file.write_text(code, encoding="utf-8")

        cmd = ["manim", "-ql", str(scene_file), scene_name]
        try:
            start_t = time.perf_counter()
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=tmpdir,
            )
            elapsed = time.perf_counter() - start_t
            if proc.returncode == 0:
                observer.success(f"Render completed cleanly in {elapsed:.2f}s!")
            else:
                observer.error(f"Render failed with return code {proc.returncode}")
                observer.console.print(f"[red]{proc.stderr[-1000:]}[/red]")
        except FileNotFoundError:
            observer.warning("`manim` executable not found in PATH. Skipping local render verification.")
        except subprocess.TimeoutExpired:
            observer.error("Manim render timed out after 60s.")
        except Exception as exc:
            observer.error(f"Render verification error: {exc}")


# ── Inspect Last Run ──────────────────────────────────────────────────────────

def inspect_last_run(run_store: HitlRunStore, observer: HitlTerminalObserver) -> None:
    """Display summary and diagnostics from the most recent run log."""
    last_run = run_store.get_last_run()
    if not last_run:
        observer.warning(f"No run logs found in {run_store.log_dir}")
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


# ── CLI Entrypoint ────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Frictionless Local Dev & Test Runner for Pydantic AI HITL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("topic", nargs="?", default="Fourier Transform", help="Topic or educational text to process")
    parser.add_argument(
        "-s", "--stage",
        choices=["all", "classify", "compose", "code", "preflight", "repair"],
        default="all",
        help="Pipeline stage to run (default: all)",
    )
    parser.add_argument("--mock", action="store_true", help="Run with Pydantic AI TestModel (offline, 0 API tokens)")
    parser.add_argument("-m", "--model", default=None, help="LLM model override (e.g. nex-agi/nex-n2.5-pro:free or gpt-4o-mini)")
    parser.add_argument("-f", "--file", default=None, help="Python source file for preflight or repair stage")
    parser.add_argument("-e", "--error", default=None, help="Traceback or compiler error for repair stage")
    parser.add_argument("--inject-mobject-bug", action="store_true", help="Inject intentional mobject index error to test repair agent")
    parser.add_argument("--render", action="store_true", help="Verify scene compilation with local `manim -ql`")
    parser.add_argument("--inspect-last", action="store_true", help="Inspect details of the most recent local run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show full prompts and verbose conversation traces")
    parser.add_argument("--log-dir", default=None, help="Custom local log storage directory")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()

    # 1. Disable Logfire remote export for local development
    disable_logfire_remote()

    run_store = HitlRunStore(log_dir=args.log_dir)
    observer = HitlTerminalObserver(verbose=args.verbose)

    if args.inspect_last:
        inspect_last_run(run_store, observer)
        return

    # Check for preflight stage on file or text
    if args.stage == "preflight":
        run_preflight_inspector(args.file, None if args.file else args.topic, observer, run_store)
        return

    start_total_t = time.perf_counter()
    observer.banner(
        "AOS HITL Local Development Runner",
        f"Mode: {'MOCK (Pydantic AI TestModel)' if args.mock else 'LIVE LLM'}  |  Stage: {args.stage.upper()}",
    )

    try:
        # Check API key if not in mock mode
        if not args.mock:
            try:
                hitl_agents._resolve_llm_config(model_name=args.model)
            except ValueError as exc:
                observer.error(str(exc))
                observer.console.print(
                    "\n[bold yellow]Tip:[/bold yellow] To test offline without an API key, add the [bold cyan]--mock[/bold cyan] flag:\n"
                    f"  [green]uv run python dev_hitl.py --mock \"{args.topic}\"[/green]\n"
                )
                return

        # STAGE: CLASSIFY
        if args.stage in ("classify", "all"):
            classify_res = await run_classify_stage(
                args.topic, observer, run_store, mock=args.mock, model_name=args.model
            )
            if not classify_res.animatable and args.stage == "all":
                observer.warning("Content classified as non-animatable. Halting pipeline.")
                return
            current_topic = classify_res.topic or args.topic
        else:
            current_topic = args.topic

        # STAGE: COMPOSE
        if args.stage in ("compose", "all"):
            plan = await run_compose_stage(
                args.topic, current_topic, observer, run_store, mock=args.mock, model_name=args.model
            )
        else:
            plan = MOCK_PLAN

        # STAGE: CODE
        if args.stage in ("code", "all"):
            code, scene_name = await run_code_stage(
                plan, current_topic, observer, run_store,
                mock=args.mock, model_name=args.model, inject_bug=args.inject_mobject_bug
            )
        elif args.file:
            code = Path(args.file).read_text(encoding="utf-8")
            scene_name = "CustomScene"
        else:
            code = MOCK_BROKEN_CODE_MOBJECT if args.inject_mobject_bug else MOCK_VALID_CODE
            scene_name = "BrokenMobjectScene" if args.inject_mobject_bug else "FourierTransformScene"

        # STAGE: REPAIR (if explicitly requested, or if preflight failed during 'all')
        if args.stage == "repair" or (args.stage == "all" and args.inject_mobject_bug):
            sample_err = args.error or (
                "IndexError: list index out of range\n"
                "  File 'scene.py', line 7, in construct\n"
                "    square = formula[5]\n"
                "IndexError: list index out of range"
            )
            repaired_code, scene_name = await run_repair_stage(
                code, sample_err, scene_name, observer, run_store, mock=args.mock, model_name=args.model
            )
            code = repaired_code

        # Optional local render
        if args.render:
            run_local_render_check(code, scene_name, observer)

        total_elapsed = time.perf_counter() - start_total_t
        observer.show_run_summary(
            stage=args.stage,
            status="success",
            duration=total_elapsed,
            usage={},
            log_path=run_store.last_run_file,
        )

    except KeyboardInterrupt:
        observer.warning("Run aborted by user.")
    except Exception as exc:
        observer.error(f"Pipeline failed: {type(exc).__name__}: {exc}")
        if args.verbose:
            import traceback
            observer.console.print(traceback.format_exc())


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

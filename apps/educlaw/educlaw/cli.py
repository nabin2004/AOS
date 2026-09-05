"""REPL, TUI, and headless entry for the EduClaw harness, powered by Typer and Rich."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.rule import Rule
from rich.table import Table
import typer

from educlaw.logo import play_logo
from educlaw.observability import configure_logfire
from educlaw.session import create_session
from educlaw.settings import PermissionMode, Settings, resolve_harness_home

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

__version__ = "0.1.0"

console = Console()
err_console = Console(stderr=True)

HELP = """Slash commands:
  /compact          squash history to [summary, *tail]
  /clear            drop message history
  /memory [query]   show strategy and optional retrieve
  /curate           run Dagestan curation (decay, contradictions)
  /abort            enqueue an abort for the next safe boundary
  /steer <text>     enqueue steering for the next model call
  /yes /no          answer a pending permission prompt (TUI)
  /help             show this help
  /quit             exit
"""


def print_slash_help(target_console: Console | None = None) -> None:
    """Render a structured Rich table of slash commands."""
    out = target_console or console
    table = Table(
        title="EduClaw Interactive Slash Commands",
        header_style="bold cyan",
        border_style="dim cyan",
        show_lines=True,
    )
    table.add_column("Command", style="bold yellow", no_wrap=True)
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("/help", "Navigation", "Show this interactive command table")
    table.add_row("/quit, /exit, /q", "Navigation", "Exit the EduClaw harness")
    table.add_row("/compact", "Session", "Squash message history into `[summary, *tail]`")
    table.add_row("/clear", "Session", "Drop conversation message history")
    table.add_row("/memory [query]", "Memory", "Display Dagestan strategy and retrieve relevant nodes")
    table.add_row("/curate", "Memory", "Run Dagestan memory curation (decay & contradiction scan)")
    table.add_row("/steer <text>", "Steering", "Enqueue guidance/steering for the next model call")
    table.add_row("/abort", "Steering", "Enqueue an abort signal for the next safe turn boundary")
    table.add_row("/yes, /y", "Permission", "Approve a pending tool permission prompt")
    table.add_row("/no, /n", "Permission", "Deny a pending tool permission prompt")

    out.print(table)


def _print_emit(event: str, payload: object, target_console: Console | None = None) -> None:
    """Rich formatted event emitter for harness runtime notifications."""
    out = target_console or console
    if event == "abort":
        out.print("[bold red][ABORT] [harness] turn aborted[/]")
    elif event == "memory_skip":
        out.print("[dim yellow][WARN] [harness] memory ingest skipped (no LLM client configured)[/]")
    elif event == "permission_required":
        out.print(
            Panel(
                f"[bold yellow]{payload}[/]\n\n[dim]Respond with [bold green]/yes[/] to approve or [bold red]/no[/] to deny.[/]",
                title="[bold yellow]Permission Required[/]",
                border_style="yellow",
            )
        )
    elif event == "tool":
        out.print(f"[dim cyan][TOOL][/] [white]{payload}[/]")
    elif event == "prompt_prep":
        if isinstance(payload, dict):
            prompt_val = payload.get("prompt", "")
            instr_val = payload.get("instructions", "")
            out.print(
                Panel(
                    f"[bold cyan]User Prompt / Input:[/]\n{prompt_val}\n\n[bold yellow]System Instructions & Injected Context:[/]\n{instr_val}",
                    title="[bold magenta]EduClaw Harness Transparency View[/]",
                    border_style="magenta",
                )
            )
    elif event == "model_start":
        model_name = payload.get("model", "") if isinstance(payload, dict) else str(payload)
        out.print(f"[bold green][LLM][/] Executing turn with model [bold cyan]{model_name}[/]...")
    else:
        out.print(f"[dim][harness] {event}: {payload}[/]")


async def _handle_slash(handler: Any, line: str, target_console: Console | None = None) -> bool:
    """Return True if the process should exit."""
    out = target_console or console
    command, _, rest = line[1:].partition(" ")
    command = command.lower().strip()
    rest = rest.strip()

    if command in {"quit", "exit", "q"}:
        out.print("[dim]Exiting EduClaw...[/]")
        return True

    if command == "help":
        print_slash_help(out)
        return False

    if command == "clear":
        handler.clear()
        out.print("[bold green][OK] [harness][/] Conversation context cleared.")
        return False

    if command == "compact":
        await handler.full_compaction()
        out.print("[bold green][OK] [harness][/] Context compacted to `[summary, *tail]`.")
        return False

    if command == "memory":
        strategy = await handler.deps.memory.strategy()
        query = rest or "user preferences goals"
        retrieved = await handler.deps.memory.retrieve(query)

        out.print(Panel(strategy or "[dim](empty strategy)[/]", title="Dagestan Memory Strategy", border_style="cyan"))
        out.print(Panel(retrieved or "[dim](no nodes matched)[/]", title=f"Retrieved Memory ({query})", border_style="blue"))
        return False

    if command == "curate":
        report = await handler.deps.memory.curate()
        contradictions = getattr(report, "contradictions_found", report)
        out.print(f"[bold green][OK] [harness][/] Memory curated. Contradictions found: [bold cyan]{contradictions}[/]")
        return False

    if command == "abort":
        handler.deps.steering.push("/abort", kind="abort")
        out.print("[bold yellow][WARN] [harness][/] Abort signal queued for next safe boundary.")
        return False

    if command == "steer":
        if not rest:
            out.print("[yellow]Usage: /steer <text>[/]")
            return False
        handler.deps.steering.push(rest, kind="steer")
        out.print(f"[bold cyan][STEER] [harness][/] Steer queued for next model call: [dim]{rest}[/]")
        return False

    if command in {"yes", "y"}:
        if handler.deps.gate.answer(True):
            out.print("[bold green][OK] [harness][/] Tool execution approved.")
        else:
            out.print("[dim][harness] No tool permission currently pending.[/]")
        return False

    if command in {"no", "n"}:
        if handler.deps.gate.answer(False):
            out.print("[bold red][DENIED] [harness][/] Tool execution denied.")
        else:
            out.print("[dim][harness] No tool permission currently pending.[/]")
        return False

    out.print(f"[bold red][ERR] [harness][/] Unknown command [bold]/{command}[/]. Type [cyan]/help[/] for available commands.")
    return False


async def stdin_permission(action: Any) -> bool:
    """Prompt user interactively in REPL to grant or deny tool execution."""
    console.print(
        Panel(
            f"[bold cyan]Kind:[/] {action.kind}\n[bold cyan]Summary:[/] {action.summary}",
            title="[bold yellow]Permission Request[/]",
            border_style="yellow",
        )
    )
    try:
        approved = await asyncio.to_thread(Confirm.ask, "[bold yellow]Allow this action?[/]", default=False)
        return approved
    except (EOFError, KeyboardInterrupt):
        return False


async def run_repl(
    cwd: Path,
    settings: Settings,
    *,
    yes: bool,
    target_console: Console | None = None,
) -> int:
    """Run the interactive coding agent REPL."""
    out = target_console or console
    handler = create_session(
        cwd=cwd,
        settings=settings,
        emit=lambda ev, py: _print_emit(ev, py, target_console=out),
        yes=yes,
        permission_resolver=None if yes else stdin_permission,
    )

    play_logo()

    welcome_table = Table.grid(padding=(0, 1))
    welcome_table.add_column(style="bold cyan", justify="right")
    welcome_table.add_column(style="white")
    welcome_table.add_row("Model:", f"[green]{settings.model}[/]")
    welcome_table.add_row("Workspace:", f"[dim]{cwd}[/]")
    welcome_table.add_row("Permissions:", f"[yellow]{'auto-approve (--yes)' if yes else settings.permission_mode}[/]")
    welcome_table.add_row("Tips:", "Type [cyan]/help[/] for commands or [cyan]/quit[/] to exit.")

    out.print(
        Panel(
            welcome_table,
            title="[bold magenta]EduClaw Manim Harness[/]",
            border_style="magenta",
            subtitle="[dim]Ready for interactive prompts[/]",
        )
    )

    while True:
        try:
            line = await asyncio.to_thread(lambda: out.input("\n[bold green]educlaw[/][bold white]>[/] ").strip())
        except (EOFError, KeyboardInterrupt):
            out.print("\n[dim]Session ended.[/]")
            return 0

        if not line:
            continue

        if line.startswith("/"):
            if await _handle_slash(handler, line, target_console=out):
                return 0
            continue

        if handler.running:
            handler.deps.steering.push(line)
            out.print("[bold cyan][STEER] [harness][/] Steer queued until next model turn.")
            continue

        try:
            out.print("[bold cyan]⠋ EduClaw executing turn...[/]")
            output = await handler.run_turn(line)
        except Exception as exc:  # noqa: BLE001 — REPL stays alive on errors
            out.print(f"[bold red][ERR] [harness error]:[/] {exc}")
            continue

        out.print(Rule(style="dim cyan"))
        out.print(Markdown(output))
        out.print(Rule(style="dim cyan"))

    return 0


async def run_headless(
    cwd: Path,
    settings: Settings,
    prompt: str,
    *,
    yes: bool,
    durable: bool,
    raw: bool = False,
    target_console: Console | None = None,
) -> int:
    """Execute a single-shot headless prompt."""
    out = target_console or console

    if durable:
        from educlaw.durable import run_durable_turn, wrap_flow

        settings.kitaru = True
        try:
            flow = wrap_flow()
            output = await flow(prompt, str(cwd))
        except RuntimeError:
            output = await run_durable_turn(prompt, cwd, settings)

        if raw:
            print(output)
        else:
            out.print(Markdown(output))
        return 0

    handler = create_session(
        cwd=cwd,
        settings=settings,
        emit=lambda ev, py: _print_emit(ev, py, target_console=out),
        yes=yes,
        headless=True,
    )
    output = await handler.run_turn(prompt)
    if raw:
        print(output)
    else:
        out.print(Markdown(output))
    return 0


# =============================================================================
# Typer CLI Definition
# =============================================================================

app = typer.Typer(
    name="educlaw",
    help="EduClaw — Manim coding-agent harness with Pydantic AI, Dagestan memory, and Docker sandbox.",
    no_args_is_help=False,
    rich_markup_mode="rich",
    add_completion=False,
)

memory_app = typer.Typer(
    name="memory",
    help="Inspect and manage the Dagestan memory graph.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(memory_app, name="memory")

course_app = typer.Typer(
    name="course",
    help="Plan, generate, render, and inspect multi-lecture educational courses.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(course_app, name="course")

flashcards_app = typer.Typer(
    name="flashcards",
    help="Generate and export active-recall Anki decks and interactive flashcards.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(flashcards_app, name="flashcards")




def _apply_setting_overrides(
    settings: Settings,
    *,
    model: str | None = None,
    permission_mode: str | None = None,
) -> Settings:
    """Apply CLI-provided overrides onto the Settings object."""
    if model:
        settings.model = model
        if model == "test":
            settings.test_model = True
    if permission_mode and permission_mode in {"default", "edit", "auto"}:
        settings.permission_mode = permission_mode  # type: ignore[assignment]
    return settings


@app.callback(invoke_without_command=True)
def default_entry(
    ctx: typer.Context,
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory (default: current working directory)."),
    ] = None,
    headless: Annotated[
        bool,
        typer.Option("--headless", help="Run single-shot prompt in headless mode then exit."),
    ] = False,
    prompt: Annotated[
        str,
        typer.Option("-p", "--prompt", help="Prompt to execute in headless mode."),
    ] = "",
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Auto-approve tool execution permissions without confirmation."),
    ] = False,
    durable: Annotated[
        bool,
        typer.Option("--durable", help="Run turn as a durable Kitaru workflow."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier (e.g. openai:gpt-4o-mini, test)."),
    ] = None,
    permission_mode: Annotated[
        Optional[str],
        typer.Option("--permission-mode", help="Permission gate mode: default | edit | auto."),
    ] = None,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", help="Display EduClaw version and exit.", is_eager=True),
    ] = None,
) -> None:
    """EduClaw — Manim coding-agent harness with Pydantic AI, Dagestan memory, and Docker sandbox."""
    if version:
        console.print(f"[bold cyan]EduClaw[/] version [bold green]{__version__}[/]")
        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model, permission_mode=permission_mode)
    configure_logfire(settings)

    if headless or prompt:
        if not prompt.strip():
            err_console.print("[bold red]Error:[/] Headless mode requires a prompt via [bold cyan]-p/--prompt[/] or the [bold cyan]run[/] command.")
            raise typer.Exit(code=2)
        code = asyncio.run(
            run_headless(resolved_cwd, settings, prompt, yes=yes, durable=durable)
        )
        raise typer.Exit(code=code)

    code = asyncio.run(run_repl(resolved_cwd, settings, yes=yes))
    raise typer.Exit(code=code)


@app.command("repl", help="Launch the interactive REPL coding agent harness.")
def repl_command(
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory (default: current working directory)."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Auto-approve tool execution permissions without confirmation."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
    permission_mode: Annotated[
        Optional[str],
        typer.Option("--permission-mode", help="Permission gate mode: default | edit | auto."),
    ] = None,
) -> None:
    """Launch the interactive REPL coding agent harness."""
    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model, permission_mode=permission_mode)
    configure_logfire(settings)

    code = asyncio.run(run_repl(resolved_cwd, settings, yes=yes))
    raise typer.Exit(code=code)


@app.command("tui", help="Launch the full Rich interactive TUI.")
def tui_command(
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory (default: current working directory)."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
    permission_mode: Annotated[
        Optional[str],
        typer.Option("--permission-mode", help="Permission gate mode: default | edit | auto."),
    ] = None,
) -> None:
    """Launch the full Rich interactive TUI."""
    from educlaw.tui import run_tui

    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model, permission_mode=permission_mode)
    configure_logfire(settings)

    code = asyncio.run(run_tui(resolved_cwd, settings))
    raise typer.Exit(code=code)


@app.command("run", help="Execute a single turn prompt in headless mode.")
def run_command(
    prompt: Annotated[str, typer.Argument(help="The prompt to send to the EduClaw agent.")],
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Auto-approve tool execution permissions."),
    ] = False,
    durable: Annotated[
        bool,
        typer.Option("--durable", help="Run turn as a durable Kitaru workflow."),
    ] = False,
    raw: Annotated[
        bool,
        typer.Option("--raw", help="Output raw response text without Markdown rendering."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
    permission_mode: Annotated[
        Optional[str],
        typer.Option("--permission-mode", help="Permission gate mode: default | edit | auto."),
    ] = None,
) -> None:
    """Execute a single turn prompt in headless mode."""
    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model, permission_mode=permission_mode)
    configure_logfire(settings)

    code = asyncio.run(
        run_headless(resolved_cwd, settings, prompt, yes=yes, durable=durable, raw=raw)
    )
    raise typer.Exit(code=code)


@app.command("animate", help="Generate educational Manim animations using single-video or full course series mode.")
def animate_command(
    prompt: Annotated[str, typer.Argument(help="Educational topic or prompt to animate.")],
    mode: Annotated[
        str,
        typer.Option("--mode", "-M", help="Generation mode: 'single' (single topic video) or 'course' (multi-lecture series)."),
    ] = "single",
    lectures: Annotated[
        int,
        typer.Option("--lectures", "-n", help="Total lectures to generate when mode is 'course'."),
    ] = 3,
    render: Annotated[
        bool,
        typer.Option("--render/--no-render", help="Whether to compile and render videos in the Manim Docker sandbox."),
    ] = True,
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
    quality: Annotated[
        str,
        typer.Option("-q", "--quality", help="Manim render quality: l, m, h, or k."),
    ] = "m",
    theme: Annotated[
        str,
        typer.Option("-t", "--theme", help="Pedagogical visual theme: dark_glass, solarized_math, clean_pastel, cyber_neon."),
    ] = "dark_glass",
    concat: Annotated[
        bool,
        typer.Option("--concat/--no-concat", help="Whether to automatically concatenate multi-scene lecture videos via ffmpeg."),
    ] = False,
    inspect_visual: Annotated[
        bool,
        typer.Option("--inspect-visual/--no-inspect-visual", help="Enable multimodal keyframe visual QA gate to catch overlaps and clipping."),
    ] = False,
) -> None:
    """Generate educational Manim animations using single-video or full course series mode."""
    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model)
    settings.manim_quality = quality  # type: ignore[assignment]
    configure_logfire(settings)

    if mode == "course":
        from educlaw.courses.contracts import Audience, RenderStatus
        from educlaw.courses.orchestrator import CourseOrchestrator

        console.print(
            Panel(
                f"[bold cyan]Course Topic:[/] {prompt}\n"
                f"[bold cyan]Total Lectures:[/] {lectures}\n"
                f"[bold cyan]Render in Sandbox:[/] {render}\n"
                f"[bold cyan]Quality:[/] {quality}\n"
                f"[bold cyan]Workspace:[/] {resolved_cwd}",
                title="[bold magenta]Starting EduClaw Course Engine (Course Mode)[/]",
                border_style="magenta",
            )
        )

        orchestrator = CourseOrchestrator(settings=settings)
        course = asyncio.run(
            orchestrator.generate_course(
                prompt,
                num_lectures=lectures,
                audience=Audience.EXPLORING,
                render=render,
                quality=quality,
                workspace_dir=resolved_cwd,
            )
        )

        _display_course_summary(course)
        return

    # Single-video mode
    from educlaw.animateworkflow.loop import WorkflowOrchestrator

    workspace_dir = resolved_cwd / "workspace" / "coder"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    orchestrator_single = WorkflowOrchestrator(
        settings=settings,
        theme=theme,
        inspect_visual=inspect_visual,
    )

    console.print(
        Panel(
            f"[bold cyan]Prompt:[/] {prompt}\n[bold cyan]Mode:[/] single\n[bold cyan]Theme:[/] {theme}\n[bold cyan]Inspect Visual:[/] {inspect_visual}\n[bold cyan]Quality:[/] {quality}\n[bold cyan]Output dir:[/] {workspace_dir}",
            title="[bold magenta]Starting Animate Workflow (Single Mode)[/]",
            border_style="magenta",
        )
    )

    state = asyncio.run(orchestrator_single.run(prompt, workspace_dir=workspace_dir))

    if state.compile_result and state.compile_result.success:
        console.print(f"[bold green][SUCCESS][/] Video rendered at: [bold cyan]{state.compile_result.output_path}[/]")
    else:
        err_console.print("[bold red][FAIL][/] Video generation could not produce a valid render.")
        raise typer.Exit(code=1)


def _display_course_summary(course: Any) -> None:
    """Helper to render a beautiful summary table for a course."""
    console.print(
        Panel(
            f"[bold yellow]Title:[/] {course.title}\n"
            f"[bold cyan]Slug:[/] {course.slug}\n"
            f"[bold green]Subject:[/] {course.syllabus.subject} | [bold green]Audience:[/] {course.syllabus.target_audience.value if hasattr(course.syllabus.target_audience, 'value') else course.syllabus.target_audience}\n"
            f"[bold white]Overview:[/] {course.syllabus.overview}",
            title="[bold green]Course Curriculum Generated[/]",
            border_style="green",
        )
    )

    table = Table(
        title=f"Lectures in '{course.title}'",
        header_style="bold cyan",
        border_style="dim cyan",
        show_lines=True,
    )
    table.add_column("Lec #", style="bold yellow", justify="center", width=6)
    table.add_column("Title", style="white", min_width=25)
    table.add_column("Status", style="bold", justify="center", width=12)
    table.add_column("Key Concepts", style="dim", min_width=25)
    table.add_column("Artifacts", style="cyan")

    for lec in course.lectures:
        status_color = "green" if lec.status.value == "rendered" else ("yellow" if lec.status.value in {"planned", "coded"} else "red")
        artifacts = []
        if lec.video_path:
            artifacts.append("video")
        if lec.final_code:
            artifacts.append("code")
        if lec.study_notes:
            artifacts.append("notes")

        table.add_row(
            str(lec.lecture_number),
            lec.spec.title,
            f"[{status_color}]{lec.status.value.upper()}[/{status_color}]",
            ", ".join(lec.spec.key_concepts) if lec.spec.key_concepts else "N/A",
            ", ".join(artifacts) if artifacts else "pending",
        )

    console.print(table)
    console.print(f"\n[bold green]✓ Course saved at:[/] [bold cyan].educlaw/courses/{course.slug}/[/]\n")


# =============================================================================
# Course Sub-Commands
# =============================================================================


@course_app.command("new", help="Plan, generate, and optionally render a new multi-lecture course.")
def course_new_command(
    prompt: Annotated[str, typer.Argument(help="Course topic or thesis to plan.")],
    lectures: Annotated[
        int,
        typer.Option("--lectures", "-n", help="Total number of lectures (1..N)."),
    ] = 3,
    audience: Annotated[
        str,
        typer.Option("--audience", "-a", help="Target audience: grade, self_learner, or exploring."),
    ] = "exploring",
    subject: Annotated[
        str,
        typer.Option("--subject", "-s", help="Subject category (e.g. Mathematics, Physics, CS)."),
    ] = "General",
    render: Annotated[
        bool,
        typer.Option("--render/--no-render", help="Whether to compile and render Manim videos in Docker sandbox."),
    ] = True,
    quality: Annotated[
        str,
        typer.Option("-q", "--quality", help="Manim render quality: l, m, h, or k."),
    ] = "m",
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
) -> None:
    """Plan and generate a new multi-lecture educational course."""
    from educlaw.courses.contracts import Audience
    from educlaw.courses.orchestrator import CourseOrchestrator

    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model)
    settings.manim_quality = quality  # type: ignore[assignment]
    configure_logfire(settings)

    audience_enum = Audience(audience) if audience in Audience._value2member_map_ else Audience.EXPLORING

    console.print(
        Panel(
            f"[bold cyan]Topic:[/] {prompt}\n"
            f"[bold cyan]Lectures:[/] {lectures}\n"
            f"[bold cyan]Audience:[/] {audience_enum.value}\n"
            f"[bold cyan]Subject:[/] {subject}\n"
            f"[bold cyan]Render:[/] {render}\n"
            f"[bold cyan]Quality:[/] {quality}",
            title="[bold magenta]Creating New EduClaw Course[/]",
            border_style="magenta",
        )
    )

    orchestrator = CourseOrchestrator(settings=settings)
    course = asyncio.run(
        orchestrator.generate_course(
            prompt,
            num_lectures=lectures,
            audience=audience_enum,
            subject=subject,
            render=render,
            quality=quality,
            workspace_dir=resolved_cwd,
        )
    )

    _display_course_summary(course)


@course_app.command("list", help="List all courses stored in the workspace.")
def course_list_command(
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
) -> None:
    """List all courses created in the workspace."""
    from educlaw.courses.storage import list_courses

    resolved_cwd = (cwd or Path.cwd()).resolve()
    manifests = list_courses(workspace_dir=resolved_cwd)

    if not manifests:
        console.print("[yellow]No courses found in workspace. Create one with `educlaw course new <topic>`[/]")
        return

    table = Table(
        title="EduClaw Courses in Workspace",
        header_style="bold cyan",
        border_style="dim cyan",
        show_lines=True,
    )
    table.add_column("Slug", style="bold yellow")
    table.add_column("Title", style="white", min_width=25)
    table.add_column("Subject", style="cyan")
    table.add_column("Audience", style="dim")
    table.add_column("Lectures", justify="center")
    table.add_column("Created", style="dim", justify="center")

    for manifest in manifests:
        table.add_row(
            manifest.slug,
            manifest.title,
            manifest.subject,
            manifest.target_audience,
            f"{manifest.rendered_lectures}/{manifest.total_lectures} rendered",
            manifest.created_at[:10] if manifest.created_at else "N/A",
        )

    console.print(table)


@course_app.command("show", help="Display details, syllabus, and lecture breakdown for a course.")
def course_show_command(
    slug: Annotated[str, typer.Argument(help="Course slug or course ID.")],
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
) -> None:
    """Display complete course syllabus, lecture breakdown, and rendering status."""
    from educlaw.courses.storage import load_course

    resolved_cwd = (cwd or Path.cwd()).resolve()
    course = load_course(slug, workspace_dir=resolved_cwd)

    if course is None:
        err_console.print(f"[bold red]Error:[/] Course '{slug}' not found.")
        raise typer.Exit(code=1)

    _display_course_summary(course)


@course_app.command("render", help="Render or re-render lectures in a course.")
def course_render_command(
    slug: Annotated[str, typer.Argument(help="Course slug or course ID.")],
    lecture: Annotated[
        Optional[int],
        typer.Option("--lecture", "-l", help="Specific lecture number to render (e.g. 1, 2). If omitted, renders all unrendered."),
    ] = None,
    quality: Annotated[
        str,
        typer.Option("-q", "--quality", help="Manim render quality: l, m, h, or k."),
    ] = "m",
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
) -> None:
    """Render one or all lectures of an existing course in Docker sandbox."""
    from educlaw.courses.contracts import RenderStatus
    from educlaw.courses.orchestrator import CourseOrchestrator
    from educlaw.courses.storage import load_course

    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model)
    settings.manim_quality = quality  # type: ignore[assignment]
    configure_logfire(settings)

    course = load_course(slug, workspace_dir=resolved_cwd)
    if course is None:
        err_console.print(f"[bold red]Error:[/] Course '{slug}' not found.")
        raise typer.Exit(code=1)

    orchestrator = CourseOrchestrator(settings=settings)

    if lecture is not None:
        target_lec = course.get_lecture(lecture)
        if target_lec is None:
            err_console.print(f"[bold red]Error:[/] Lecture {lecture} not found in course '{course.slug}'.")
            raise typer.Exit(code=1)
        console.print(f"[bold cyan]Rendering Lecture {lecture}:[/] {target_lec.spec.title}...")
        asyncio.run(
            orchestrator.generate_lecture(
                course,
                lecture,
                render=True,
                quality=quality,
                workspace_dir=resolved_cwd,
            )
        )
    else:
        console.print(f"[bold cyan]Rendering all pending lectures for course '{course.slug}'...[/]")
        asyncio.run(
            orchestrator.resume_course(
                course.slug,
                render=True,
                quality=quality,
                workspace_dir=resolved_cwd,
            )
        )

    # Reload updated course
    updated_course = load_course(course.slug, workspace_dir=resolved_cwd)
    if updated_course:
        _display_course_summary(updated_course)


@course_app.command("resume", help="Resume generation/rendering of an interrupted or failed course.")
def course_resume_command(
    slug: Annotated[str, typer.Argument(help="Course slug or course ID.")],
    quality: Annotated[
        str,
        typer.Option("-q", "--quality", help="Manim render quality: l, m, h, or k."),
    ] = "m",
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
) -> None:
    """Resume an interrupted or failed course generation."""
    from educlaw.courses.orchestrator import CourseOrchestrator
    from educlaw.courses.storage import load_course

    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model)
    settings.manim_quality = quality  # type: ignore[assignment]
    configure_logfire(settings)

    orchestrator = CourseOrchestrator(settings=settings)
    course = asyncio.run(
        orchestrator.resume_course(
            slug,
            render=True,
            quality=quality,
            workspace_dir=resolved_cwd,
        )
    )
    _display_course_summary(course)


@course_app.command("export", help="Export complete course handbook (syllabus + all lecture notes) to a single Markdown file.")
def course_export_command(
    slug: Annotated[str, typer.Argument(help="Course slug or course ID.")],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Destination Markdown file path."),
    ] = None,
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
) -> None:
    """Export the complete course handbook (syllabus + companion lecture study notes)."""
    from educlaw.courses.storage import export_course_handbook, load_course

    resolved_cwd = (cwd or Path.cwd()).resolve()
    course = load_course(slug, workspace_dir=resolved_cwd)
    if course is None:
        err_console.print(f"[bold red]Error:[/] Course '{slug}' not found.")
        raise typer.Exit(code=1)

    dest_file = output or (resolved_cwd / ".educlaw" / "courses" / course.slug / f"{course.slug}_handbook.md")
    export_course_handbook(course, output_file=dest_file)
    console.print(f"[bold green]✓ Course handbook exported to:[/] [bold cyan]{dest_file}[/]")


@course_app.command("flashcards", help="Generate Anki-compatible flashcards for a course or specific lecture.")
def course_flashcards_command(
    slug: Annotated[str, typer.Argument(help="Course slug or course ID.")],
    lecture: Annotated[
        Optional[int],
        typer.Option("--lecture", "-l", help="Specific lecture number. If omitted, generates flashcards for all lectures."),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format: 'anki' (TSV/TXT), 'markdown' (interactive .md), or 'json'."),
    ] = "anki",
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Custom output file destination."),
    ] = None,
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
) -> None:
    """Generate active-recall Anki flashcards from course lecture materials."""
    from educlaw.courses.storage import load_course
    from educlaw.flashcards.contracts import ExportFormat
    from educlaw.flashcards.exporters import export_deck
    from educlaw.flashcards.generator import FlashcardGenerator

    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model)
    configure_logfire(settings)

    course = load_course(slug, workspace_dir=resolved_cwd)
    if course is None:
        err_console.print(f"[bold red]Error:[/] Course '{slug}' not found.")
        raise typer.Exit(code=1)

    export_fmt = ExportFormat.ANKI_TSV if format in {"anki", "tsv", "txt"} else (ExportFormat.MARKDOWN if format in {"md", "markdown"} else ExportFormat.JSON)
    generator = FlashcardGenerator(settings=settings)

    if lecture is not None:
        console.print(f"[bold cyan]Generating flashcards for Lecture {lecture}...[/]")
        deck = asyncio.run(generator.generate_from_lecture(course, lecture))
        ext = "anki.txt" if export_fmt == ExportFormat.ANKI_TSV else ("md" if export_fmt == ExportFormat.MARKDOWN else "json")
        dest_file = output or (resolved_cwd / ".educlaw" / "courses" / course.slug / f"lecture_{lecture:02d}" / f"flashcards.{ext}")
        export_deck(deck, format_type=export_fmt, output_path=dest_file)
        console.print(f"[bold green]✓ Generated {deck.total_cards} cards for Lecture {lecture}:[/] [bold cyan]{dest_file}[/]")
    else:
        console.print(f"[bold cyan]Generating flashcard decks for all lectures in '{course.title}'...[/]")
        total_created = 0
        for lec in course.lectures:
            deck = asyncio.run(generator.generate_from_lecture(course, lec.lecture_number))
            ext = "anki.txt" if export_fmt == ExportFormat.ANKI_TSV else ("md" if export_fmt == ExportFormat.MARKDOWN else "json")
            dest_file = resolved_cwd / ".educlaw" / "courses" / course.slug / f"lecture_{lec.lecture_number:02d}" / f"flashcards.{ext}"
            export_deck(deck, format_type=export_fmt, output_path=dest_file)
            total_created += deck.total_cards
            console.print(f"  - Lecture {lec.lecture_number}: {deck.total_cards} cards -> [dim]{dest_file.name}[/]")

        if output:
            # Also compile whole-course deck if output specified
            ext = "anki.txt" if export_fmt == ExportFormat.ANKI_TSV else ("md" if export_fmt == ExportFormat.MARKDOWN else "json")
            combined_dest = output
            # Generate whole course deck from syllabus
            course_deck = asyncio.run(
                generator.generate_from_prompt(
                    topic=course.title,
                    title=f"{course.title} (Complete Deck)",
                    context=f"Course Syllabus:\n{course.syllabus.model_dump_json()}",
                )
            )
            export_deck(course_deck, format_type=export_fmt, output_path=combined_dest)
            console.print(f"[bold green]✓ Course master deck exported to:[/] [bold cyan]{combined_dest}[/]")


# =============================================================================
# Standalone Flashcards Sub-Commands
# =============================================================================


@flashcards_app.command("new", help="Generate Anki-compatible flashcards for any educational topic.")
def flashcards_new_command(
    prompt: Annotated[str, typer.Argument(help="Educational concept or topic to generate cards for.")],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format: 'anki' (TSV/TXT), 'markdown' (interactive .md), or 'json'."),
    ] = "anki",
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Custom output file destination."),
    ] = None,
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("-m", "--model", help="Override the LLM model identifier."),
    ] = None,
) -> None:
    """Generate high-yield active recall flashcards ready for Anki import."""
    from educlaw.flashcards.contracts import ExportFormat
    from educlaw.flashcards.exporters import export_deck
    from educlaw.flashcards.generator import FlashcardGenerator

    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    _apply_setting_overrides(settings, model=model)
    configure_logfire(settings)

    export_fmt = ExportFormat.ANKI_TSV if format in {"anki", "tsv", "txt"} else (ExportFormat.MARKDOWN if format in {"md", "markdown"} else ExportFormat.JSON)
    generator = FlashcardGenerator(settings=settings)

    console.print(
        Panel(
            f"[bold cyan]Topic:[/] {prompt}\n[bold cyan]Format:[/] {export_fmt.value}",
            title="[bold magenta]Generating Active Recall Flashcards[/]",
            border_style="magenta",
        )
    )

    deck = asyncio.run(generator.generate_from_prompt(topic=prompt))

    ext = "anki.txt" if export_fmt == ExportFormat.ANKI_TSV else ("md" if export_fmt == ExportFormat.MARKDOWN else "json")
    slug = re.sub(r"[^\w\s-]", "", prompt.lower()).strip().replace(" ", "-") or "flashcards"
    dest_file = output or (resolved_cwd / ".educlaw" / "flashcards" / f"{slug}.{ext}")

    export_deck(deck, format_type=export_fmt, output_path=dest_file)

    console.print(f"[bold green]✓ Generated {deck.total_cards} cards![/]")
    console.print(f"[bold green]✓ Deck exported to:[/] [bold cyan]{dest_file}[/]")

    # Print preview table
    table = Table(
        title=f"Flashcards Preview: {deck.title}",
        header_style="bold cyan",
        border_style="dim cyan",
        show_lines=True,
    )
    table.add_column("#", justify="center", width=4)
    table.add_column("Type", style="yellow", justify="center", width=12)
    table.add_column("Front / Prompt", style="white", min_width=30)
    table.add_column("Back / Answer", style="dim", min_width=30)

    for idx, card in enumerate(deck.cards, start=1):
        front_display = card.cloze_text if card.cloze_text else card.front
        table.add_row(str(idx), card.card_type.value.upper(), front_display, card.back)

    console.print(table)






@app.command("doctor", help="Check system health, LLM keys, Docker daemon, and harness tools.")
def doctor_command(
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
) -> None:
    """Check system health, LLM keys, Docker daemon, and harness tools."""
    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    harness_home = resolve_harness_home(resolved_cwd, settings)

    table = Table(
        title="EduClaw Health & Environment Check",
        header_style="bold cyan",
        border_style="dim cyan",
        show_lines=True,
    )
    table.add_column("Component", style="bold", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Details", style="dim")

    # Python Version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 12):
        table.add_row("Python Version", "[bold green][OK] Compatible[/]", f"{py_ver} (>= 3.12 required)")
    else:
        table.add_row("Python Version", "[bold red][FAIL] Incompatible[/]", f"{py_ver} (>= 3.12 required)")

    # Model configuration
    table.add_row("Agent Model", "[bold green][OK] Configured[/]", settings.model)

    # API Keys & Local Ollama verification
    is_ollama_model = settings.model.startswith("ollama:")
    has_key = bool(settings.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
    if is_ollama_model:
        table.add_row("LLM API Key", "[bold green][OK] Local Ollama[/]", "Ollama endpoint active (no external API key required)")
    elif has_key or settings.test_model:
        table.add_row("LLM API Key", "[bold green][OK] Configured[/]", "Present in environment or test model active")
    else:
        table.add_row("LLM API Key", "[bold yellow][WARN] Missing[/]", "Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or EDUCLAW_API_KEY")

    # Local Ollama Health & Model Check
    if is_ollama_model or settings.ollama_base_url:
        import json
        import urllib.request
        base_url = settings.ollama_base_url or "http://localhost:11434/v1"
        target_model = settings.model.removeprefix("ollama:")
        # Convert http://localhost:11434/v1 -> http://localhost:11434/api/tags
        host_url = base_url.rsplit("/v1", 1)[0].rstrip("/") + "/api/tags"
        try:
            req = urllib.request.Request(host_url, headers={"User-Agent": "EduClaw"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    models = [m.get("name", "") for m in data.get("models", [])]
                    # Check matching model name or substring
                    model_found = any(target_model in m or m.startswith(target_model) for m in models)
                    if model_found:
                        table.add_row("Ollama Service", "[bold green][OK] Running & Ready[/]", f"Model '{target_model}' found in local Ollama ({len(models)} models available)")
                    else:
                        table.add_row("Ollama Service", "[bold yellow][WARN] Model Missing[/]", f"Ollama is running, but '{target_model}' not found in local models: {', '.join(models[:3])}")
                else:
                    table.add_row("Ollama Service", "[bold yellow][WARN] HTTP Error[/]", f"Ollama endpoint responded with status {resp.status}")
        except Exception as exc:
            table.add_row("Ollama Service", "[bold yellow][WARN] Offline[/]", f"Could not connect to Ollama at {host_url}: {exc}")

    # Docker Daemon
    docker_bin = shutil.which("docker")
    if docker_bin:
        try:
            res = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=3,encoding="utf-8",errors="replace",check=False)
            if res.returncode == 0:
                table.add_row("Docker Daemon", "[bold green][OK] Running[/]", f"Sandbox image: {settings.manim_image}")
            else:
                table.add_row("Docker Daemon", "[bold yellow][WARN] Offline[/]", "Docker CLI found, but daemon not running")
        except Exception:
            table.add_row("Docker Daemon", "[bold yellow][WARN] Timeout[/]", "Could not connect to Docker daemon")
    else:
        table.add_row("Docker Daemon", "[bold yellow][WARN] Not Found[/]", "Docker CLI not found in PATH (needed for sandboxed Manim renders)")

    # Ty LSP Diagnostics
    ty_bin = shutil.which("ty")
    if ty_bin:
        table.add_row("Ty LSP / Checker", "[bold green][OK] Available[/]", ty_bin)
    else:
        table.add_row("Ty LSP / Checker", "[dim][--] Optional[/]", "Fast AST syntax checking active via ast.parse fallback")

    # Dagestan Memory Store
    memory_graph_path = harness_home / "memory" / "graph.json"
    if memory_graph_path.exists():
        size = memory_graph_path.stat().st_size
        table.add_row("Memory Graph", "[bold green][OK] Active[/]", f"{memory_graph_path} ({size} bytes)")
    else:
        table.add_row("Memory Graph", "[dim][--] New[/]", f"Initialized on first run: {memory_graph_path}")

    # Harness Home Directory
    table.add_row("Harness Home", "[bold green][OK] Ready[/]", str(harness_home))

    console.print(table)


@app.command("config", help="Display active EduClaw configuration and environment settings.")
def config_command() -> None:
    """Display active EduClaw configuration and environment settings."""
    settings = Settings.from_env()

    table = Table(
        title="Active EduClaw Settings",
        header_style="bold magenta",
        border_style="dim magenta",
        show_lines=True,
    )
    table.add_column("Setting", style="bold cyan")
    table.add_column("Value", style="white")
    table.add_column("Env Variable", style="dim")

    table.add_row("Model", str(settings.model), "EDUCLAW_MODEL")
    table.add_row("API Key Configured", "Yes" if settings.api_key else "No", "EDUCLAW_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY")
    table.add_row("Permission Mode", str(settings.permission_mode), "EDUCLAW_PERMISSION_MODE")
    table.add_row("Harness Home", str(settings.harness_home or "<cwd>/.aos"), "EDUCLAW_HARNESS_HOME")
    table.add_row("Context Window Tokens", str(settings.context_window_tokens or "Default"), "EDUCLAW_CONTEXT_WINDOW")
    table.add_row("Compaction Threshold", str(settings.compaction_threshold), "EDUCLAW_COMPACTION_THRESHOLD")
    table.add_row("Compaction Tail", str(settings.compaction_tail), "EDUCLAW_COMPACTION_TAIL")
    table.add_row("Memory Digest Every", str(settings.memory_digest_every), "EDUCLAW_MEMORY_DIGEST_EVERY")
    table.add_row("Memory Stub Mode", str(settings.memory_stub), "EDUCLAW_MEMORY_STUB")
    table.add_row("Test Model Mode", str(settings.test_model), "EDUCLAW_TEST_MODEL")
    table.add_row("Manim Docker Image", str(settings.manim_image), "EDUCLAW_MANIM_IMAGE")
    table.add_row("Manim Quality", str(settings.manim_quality), "EDUCLAW_MANIM_QUALITY")
    table.add_row("Kitaru Durability", str(settings.kitaru), "EDUCLAW_KITARU")
    table.add_row("Logfire Instrumentation", str(settings.logfire), "EDUCLAW_LOGFIRE / LOGFIRE_TOKEN")

    console.print(table)


@memory_app.command("show", help="Display current Dagestan memory strategy and status.")
def memory_show_command(
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
) -> None:
    """Display current Dagestan memory strategy and status."""
    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    handler = create_session(cwd=resolved_cwd, settings=settings, headless=True)

    async def _show() -> None:
        strategy = await handler.deps.memory.strategy()
        console.print(Panel(strategy or "[dim](empty strategy)[/]", title="Dagestan Memory Strategy", border_style="cyan"))

    asyncio.run(_show())


@memory_app.command("query", help="Query the Dagestan memory graph.")
def memory_query_command(
    query: Annotated[str, typer.Argument(help="Search query to retrieve relevant memory nodes.")],
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
) -> None:
    """Query the Dagestan memory graph."""
    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    handler = create_session(cwd=resolved_cwd, settings=settings, headless=True)

    async def _query() -> None:
        retrieved = await handler.deps.memory.retrieve(query)
        console.print(Panel(retrieved or "[dim](no nodes matched)[/]", title=f"Retrieved Memory ({query})", border_style="blue"))

    asyncio.run(_query())


@memory_app.command("curate", help="Run Dagestan memory curation to resolve contradictions and apply decay.")
def memory_curate_command(
    cwd: Annotated[
        Optional[Path],
        typer.Option("--cwd", "-C", help="Workspace root directory."),
    ] = None,
) -> None:
    """Run Dagestan memory curation to resolve contradictions and apply decay."""
    resolved_cwd = (cwd or Path.cwd()).resolve()
    settings = Settings.from_env()
    handler = create_session(cwd=resolved_cwd, settings=settings, headless=True)

    async def _curate() -> None:
        report = await handler.deps.memory.curate()
        contradictions = getattr(report, "contradictions_found", report)
        console.print(f"[bold green][OK] [memory][/] Memory curated successfully. Contradictions found: [bold cyan]{contradictions}[/]")

    asyncio.run(_curate())


@app.command("version", help="Show EduClaw version.")
def version_command() -> None:
    """Show EduClaw version."""
    console.print(f"[bold cyan]EduClaw[/] version [bold green]{__version__}[/]")


# =============================================================================
# Programmatic / Legacy Compatibility Entrypoints
# =============================================================================

def build_parser() -> Any:
    """Legacy parser builder for backwards compatibility."""
    import argparse

    parser = argparse.ArgumentParser(description="EduClaw coding harness (legacy parser)")
    parser.add_argument("command", nargs="?", choices=["tui", "repl", "run", "doctor", "config"], help="Optional command")
    parser.add_argument("--cwd", type=Path, default=None, help="Workspace root")
    parser.add_argument("--headless", action="store_true", help="Single-shot run, then exit")
    parser.add_argument("-p", "--prompt", default="", help="Prompt for --headless")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-approve tool permissions")
    parser.add_argument("--durable", action="store_true", help="Run headless turn as a Kitaru flow")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Main entrypoint invoked by `educlaw` script in pyproject.toml and main.py.
    Returns integer exit code.
    """
    if argv is None:
        argv = sys.argv[1:]
    try:
        res = app(args=argv, standalone_mode=False)
        if isinstance(res, int):
            return res
        return 0
    except (typer.Exit, typer.Abort) as exc:
        return getattr(exc, "exit_code", 1)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        return 0 if exc.code is None else 1
    except Exception as exc:
        # Check if click / typer exit exception
        if hasattr(exc, "exit_code") and isinstance(getattr(exc, "exit_code"), int):
            return getattr(exc, "exit_code")
        err_console.print(f"[bold red]Error:[/] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

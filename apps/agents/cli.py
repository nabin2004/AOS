"""Animus — CLI for the AOS lecture-generation pipeline.

    $ animus generate "explain the derivative of x squared"
    $ animus animate "I want to see Euler's formula visually"

Run with: uv run python cli.py generate|animate "..."   (from apps/agents)
"""

from __future__ import annotations

import asyncio
import sys

import typer
from dotenv import load_dotenv
from pydantic_graph import EndMarker
from rich.console import Console
from rich.panel import Panel

load_dotenv()

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

console = Console()
app = typer.Typer(
    name="animus",
    help="Animus — AOS lecture-generation pipeline CLI.",
    no_args_is_help=False,
    add_completion=False,
)


def _show_banner() -> None:
    try:
        from terminaltexteffects.effects.effect_decrypt import Decrypt

        effect = Decrypt("ANIMUS")
        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)
    except Exception:
        console.print(
            Panel.fit("[bold cyan]ANIMUS[/]", subtitle="AOS lecture pipeline")
        )


def _show_command_help() -> None:
    console.print("Usage:")
    console.print('  animus generate "<request>" [--max-repairs N] [--no-banner]')
    console.print('  animus animate "<request>" [--no-banner]')


async def _run_full_pipeline(user_request: str, max_validation_attempts: int):
    from graph import AnimationState, animation_graph

    state = AnimationState(
        user_request=user_request, max_validation_attempts=max_validation_attempts
    )
    output = ""
    async with animation_graph.iter(state=state) as run:
        async for step in run:
            if isinstance(step, EndMarker):
                output = step.value
                break
            for task in step:
                console.print(f"[dim]-> {task.node_id}[/]")
    return state, output


async def _run_animate_pipeline(user_request: str) -> dict:
    from agent_graph import animation_graph as animate_graph
    from agent_graph import AnimationState as AnimateState
    from ir.manim_ir import Subject

    state = AnimateState(user_query=user_request)
    async with animate_graph.iter(state=state) as run:
        async for step in run:
            if isinstance(step, EndMarker):
                break
            for task in step:
                console.print(f"[dim]-> {task.node_id}[/]")

    if state.coder_result is not None:
        return state.coder_result.model_dump(mode="json")
    if state.classification is None or state.classification.subject == Subject.UNKNOWN:
        return {
            "stopped_reason": "classification_failed_or_unsupported",
            "compile_ok": False,
            "message": "Domain not supported or classification failed.",
        }
    return {
        "stopped_reason": "unknown",
        "compile_ok": False,
        "message": "Pipeline ended without coder result.",
    }


def _print_animate_result(result: dict) -> None:
    lines = [
        f"stopped_reason: {result.get('stopped_reason', '?')}",
        f"compile_ok: {result.get('compile_ok', False)}",
        f"scene_name: {result.get('scene_name') or '—'}",
        f"run_dir: {result.get('run_dir') or '—'}",
        f"audio: {len(result.get('audio_paths') or [])}",
    ]
    if result.get("summary"):
        lines.append(f"summary: {result['summary']}")
    if result.get("message"):
        lines.append(f"message: {result['message']}")
    console.print(Panel.fit("\n".join(lines), title="Animation result"))


@app.command()
def generate(
    request: str = typer.Argument(..., help="What the lecture should teach"),
    max_repairs: int = typer.Option(
        3, "--max-repairs", help="Max validation-repair attempts"
    ),
    banner: bool = typer.Option(
        True, "--banner/--no-banner", help="Show the intro effect"
    ),
) -> None:
    """Run the full IR lecture pipeline (storyboard → beats → validate → inspect)."""
    if banner:
        _show_banner()

    console.print(Panel.fit(f"[bold]{request}[/]", title="Generating lecture"))
    try:
        state, summary = asyncio.run(_run_full_pipeline(request, max_repairs))
    except Exception as exc:
        console.print(f"[bold red]Pipeline failed:[/] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        Panel.fit(summary or "[dim]no summary[/]", title="Inspection summary")
    )
    if state.validation_result and not state.validation_result.passed:
        console.print(
            f"[yellow]Validation did not fully pass after {state.validation_attempts} attempt(s):[/]"
        )
        for issue in state.validation_result.issues:
            console.print(f"  - {issue}")


@app.command()
def animate(
    request: str = typer.Argument(..., help="What the Manim animation should teach"),
    banner: bool = typer.Option(
        True, "--banner/--no-banner", help="Show the intro effect"
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        help="Skip narration synthesis during coding (faster compile; sets AOS_SFT_BATCH=1)",
    ),
) -> None:
    """Run the animation pipeline (classify → plan → Manim coder → compile)."""
    import os

    from llm_config import PipelineEnvError, validate_pipeline_env

    if fast:
        os.environ["AOS_SFT_BATCH"] = "1"

    if banner:
        _show_banner()

    try:
        env = validate_pipeline_env()
    except PipelineEnvError as exc:
        console.print(f"[bold red]Preflight failed:[/]\n{exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        Panel.fit(
            f"[bold]{request}[/]\n[dim]profile={env['profile']}[/]",
            title="Animating",
        )
    )
    for role in ("classifier", "planner", "coder"):
        console.print(f"[dim]  {role}: {env[role]}[/]")

    try:
        result = asyncio.run(_run_animate_pipeline(request))
    except Exception as exc:
        console.print(f"[bold red]Pipeline failed:[/] {exc}")
        raise typer.Exit(code=1) from exc

    _print_animate_result(result)

    if not result.get("compile_ok"):
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _show_banner()
        _show_command_help()


if __name__ == "__main__":
    app()

"""Animus — CLI for the AOS lecture-generation pipeline.

    $ animus generate "explain the derivative of x squared"
    $ animus generate "..." --max-repairs 5 --no-banner

Runs apps/agents/graph.py end-to-end:
Classify -> PlanLecture -> MakeStoryboard -> CreateScenes -> AddBeats ->
AddNarration -> Validate (<-> Repair) -> Inspect.

Run with: uv run python cli.py generate "..."   (from apps/agents)
"""
from __future__ import annotations

import asyncio
import sys

import typer
from pydantic_graph import EndMarker
from rich.console import Console
from rich.panel import Panel

from graph import AnimationState, animation_graph

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
        console.print(Panel.fit("[bold cyan]ANIMUS[/]", subtitle="AOS lecture pipeline"))


def _show_command_help() -> None:
    console.print('Usage: animus generate "<request>" [--max-repairs N] [--no-banner]')


async def _run_pipeline(user_request: str, max_validation_attempts: int) -> tuple[AnimationState, str]:
    state = AnimationState(user_request=user_request, max_validation_attempts=max_validation_attempts)
    output = ""
    async with animation_graph.iter(state=state) as run:
        async for step in run:
            if isinstance(step, EndMarker):
                output = step.value
                break
            for task in step:
                console.print(f"[dim]-> {task.node_id}[/]")
    return state, output


@app.command()
def generate(
    request: str = typer.Argument(..., help="What the lecture should teach"),
    max_repairs: int = typer.Option(3, "--max-repairs", help="Max validation-repair attempts"),
    banner: bool = typer.Option(True, "--banner/--no-banner", help="Show the intro effect"),
) -> None:
    """Run the full lecture pipeline end-to-end for REQUEST."""
    if banner:
        _show_banner()

    console.print(Panel.fit(f"[bold]{request}[/]", title="Generating lecture"))
    try:
        state, summary = asyncio.run(_run_pipeline(request, max_repairs))
    except Exception as exc:
        console.print(f"[bold red]Pipeline failed:[/] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(Panel.fit(summary or "[dim]no summary[/]", title="Inspection summary"))
    if state.validation_result and not state.validation_result.passed:
        console.print(
            f"[yellow]Validation did not fully pass after {state.validation_attempts} attempt(s):[/]"
        )
        for issue in state.validation_result.issues:
            console.print(f"  - {issue}")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _show_banner()
        _show_command_help()


if __name__ == "__main__":
    app()

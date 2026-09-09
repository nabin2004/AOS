"""Animus — CLI for the AOS lecture-generation pipeline.

    $ animus generate "explain the derivative of x squared"
    $ animus animate "I want to see Euler's formula visually"

Run with: uv run python cli.py generate|animate "..."   (from apps/agents)

JSON mode (for UI/Celery subprocess):
    $ uv run python cli.py animate "…" --json --no-banner
    $ uv run python cli.py generate "…" --json --no-banner
"""

from __future__ import annotations

import asyncio
import json
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
    console.print('  animus generate "<request>" [--max-repairs N] [--no-banner] [--json]')
    console.print(
        '  animus animate "<request>" [--no-banner] [--json] [--output-dir DIR]'
    )


def _emit_json(payload: dict) -> None:
    """Write a single JSON object to stdout (no Rich chrome)."""
    sys.stdout.write(json.dumps(payload, default=str))
    sys.stdout.write("\n")
    sys.stdout.flush()


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


async def _run_animate_pipeline(user_request: str, length: str = "medium", cinematic: bool = False) -> dict:
    from agent_graph import animation_graph as animate_graph
    from agent_graph import AnimationState as AnimateState
    from cinematic_director import is_cinematic_mode
    from ir.manim_ir import Subject

    cinematic_active = is_cinematic_mode(user_request, flag=cinematic)
    state = AnimateState(user_query=user_request, target_length=length, cinematic=cinematic_active)
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
            "error": "classification_failed_or_unsupported",
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
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print a single JSON VideoArtifact to stdout (for UI/Celery)",
    ),
) -> None:
    """Run the full IR lecture pipeline and assemble lecture_final.mp4."""
    if as_json:
        from video_entry import run_lecture

        artifact = asyncio.run(
            run_lecture(request, max_validation_attempts=max_repairs)
        )
        _emit_json(artifact.model_dump(mode="json"))
        raise typer.Exit(code=0 if artifact.ok else 1)

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
        help=(
            "Skip synthesize_narration preview tool only (sets AOS_SFT_BATCH=1). "
            "Does NOT disable VoiceoverScene / in-scene voiceover."
        ),
    ),
    cinematic: bool = typer.Option(
        False,
        "--cinematic",
        "-c",
        help=(
            "Enable cinematic mode: high-production visual aesthetic, multi-axis camera orbits, "
            "and SciPy/NumPy velocity gradient simulation."
        ),
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print a single JSON VideoArtifact to stdout (for UI/Celery/OpenCode)",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        help="Copy/symlink final video + scene into this directory when compile succeeds",
    ),
    length: str = typer.Option(
        "medium",
        "--length",
        "-l",
        help="Target video length / pacing: 'short' (~1-2m), 'medium' / '5m' (~3-5m), 'long' / '10m' (~5-10m), or explicit duration e.g. '5m', '10m', '300s'",
    ),
) -> None:
    """Run the animation pipeline (classify → plan → Manim coder → compile)."""
    import os

    from cinematic_director import is_cinematic_mode
    from llm_config import PipelineEnvError, validate_pipeline_env

    if fast:
        os.environ["AOS_SFT_BATCH"] = "1"
    if cinematic or is_cinematic_mode(request):
        os.environ["AOS_CINEMATIC_MODE"] = "1"

    req_lower = request.lower()
    chosen_length = length
    if chosen_length == "medium":
        if any(k in req_lower for k in ("10 minutes", "10 minute", "10m", "long video")):
            chosen_length = "10m"
        elif any(k in req_lower for k in ("5 minutes", "5 minute", "5m", "at least 5")):
            chosen_length = "5m"
        elif any(k in req_lower for k in ("1 minute", "quick", "short", "brief")):
            chosen_length = "short"

    if chosen_length in ("10m", "long", "10"):
        os.environ["AOS_RENDER_TIMEOUT_SECONDS"] = os.getenv("AOS_RENDER_TIMEOUT_SECONDS", "1200")
    elif chosen_length in ("5m", "medium", "5"):
        os.environ["AOS_RENDER_TIMEOUT_SECONDS"] = os.getenv("AOS_RENDER_TIMEOUT_SECONDS", "900")

    if as_json:
        from video_entry import run_animate

        try:
            validate_pipeline_env()
        except PipelineEnvError as exc:
            _emit_json(
                {
                    "ok": False,
                    "mode": "animate",
                    "video_path": None,
                    "scene_path": None,
                    "run_dir": None,
                    "scene_file": None,
                    "has_audio": None,
                    "trajectory_path": None,
                    "error": str(exc),
                    "detail": {},
                }
            )
            raise typer.Exit(code=1) from exc

        artifact = asyncio.run(run_animate(request, output_dir=output_dir, length=chosen_length, cinematic=cinematic))
        payload = artifact.model_dump(mode="json")
        _emit_json(payload)
        # Fail when compile failed, missing video, or MP4 has no audio stream.
        ok = bool(artifact.ok and artifact.video_path)
        if ok and artifact.has_audio is False:
            ok = False
        raise typer.Exit(code=0 if ok else 1)

    if banner:
        _show_banner()

    try:
        env = validate_pipeline_env()
    except PipelineEnvError as exc:
        console.print(f"[bold red]Preflight failed:[/]\n{exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        Panel.fit(
            f"[bold]{request}[/]\n[dim]profile={env['profile']} length={chosen_length}[/]",
            title="Animating",
        )
    )
    for role in ("classifier", "planner", "coder"):
        console.print(f"[dim]  {role}: {env[role]}[/]")

    try:
        result = asyncio.run(_run_animate_pipeline(request, length=chosen_length))
    except Exception as exc:
        console.print(f"[bold red]Pipeline failed:[/] {exc}")
        raise typer.Exit(code=1) from exc

    if output_dir and result.get("compile_ok") and result.get("run_dir"):
        from video_entry import _stage_output_dir, find_mp4

        mp4 = find_mp4(result.get("run_dir"), scene_name=result.get("scene_name"))
        staged = _stage_output_dir(
            output_dir,
            video_path=str(mp4) if mp4 else None,
            scene_path=result.get("scene_file"),
        )
        console.print(f"[dim]Staged to {staged.get('output_dir')}[/]")

    _print_animate_result(result)

    if not result.get("compile_ok"):
        raise typer.Exit(code=1)
    if result.get("has_audio") is False:
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _show_banner()
        _show_command_help()


if __name__ == "__main__":
    app()

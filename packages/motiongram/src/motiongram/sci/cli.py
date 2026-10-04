"""CLI commands for MotionGram Scientific Animation DSL."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from motiongram.sci.compiler import ScientificCompiler
from motiongram.sci.schema import ScientificSceneSpec
from motiongram.sci.validator import DefensibilityValidator

sci_app = typer.Typer(
    help="Scientific simulation and animation commands (ODE, Lorenz, Chaos).",
    no_args_is_help=True,
)
console = Console()


@sci_app.command(name="schema")
def dump_schema():
    """Print the JSON schema for ScientificSceneSpec."""
    schema = ScientificSceneSpec.model_json_schema()
    typer.echo(json.dumps(schema, indent=2))


@sci_app.command(name="solve")
def solve_command(
    spec_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to scientific scene YAML specification.",
        ),
    ],
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            "-q",
            help="Simulation quality profile (preview or final).",
        ),
    ] = "final",
):
    """Precompute numerical ODE simulations and cache results."""
    with open(spec_path, encoding="utf-8") as f:
        raw_dict = yaml.safe_load(f)

    spec = ScientificSceneSpec.model_validate(raw_dict)
    compiler = ScientificCompiler()
    results = compiler.solve_data(spec, quality=quality)

    table = Table(title=f"Scientific Simulation Results: {spec.scene.id}")
    table.add_column("Data ID", style="cyan")
    table.add_column("Source", style="magenta")
    table.add_column("Points Count", justify="right", style="green")
    table.add_column("Status", style="bold")

    for ds in spec.data:
        res = results.get(ds.id)
        if res:
            table.add_row(ds.id, ds.source, str(len(res.points)), res.status)
        else:
            table.add_row(ds.id, ds.source, "0", "not computed")

    console.print(table)


@sci_app.command(name="compile")
def compile_command(
    spec_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to scientific scene YAML specification.",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Target output Python file path.",
        ),
    ] = None,
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            "-q",
            help="Quality profile (preview or final).",
        ),
    ] = "final",
):
    """Compile scientific YAML specification into Manim Python script."""
    with open(spec_path, encoding="utf-8") as f:
        yaml_content = f.read()

    py_code = ScientificCompiler.compile_yaml(yaml_content, quality=quality)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(py_code)
        console.print(f"[green]Compiled scene script written to {output}[/green]")
    else:
        typer.echo(py_code)


# Quality presets: name -> (manim_flag, width, height, default_fps)
# width=0 means use manim_flag's default resolution
_QUALITY_PRESETS: dict[str, tuple[str, int, int, int]] = {
    "preview": ("-ql", 0, 0, 30),      # 854x480
    "medium":  ("-qm", 0, 0, 30),      # 1280x720
    "high":    ("-qh", 0, 0, 60),      # 1920x1080
    "ultra":   ("-qk", 0, 0, 60),      # 2560x1440 (Manim's "4K" flag)
    "4k":      ("-qh", 3840, 2160, 60), # true 4K via --resolution override
}


@sci_app.command(name="render")
def render_command(
    spec_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to scientific scene YAML specification.",
        ),
    ],
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            "-q",
            help="Quality preset: preview | medium | high | ultra | 4k  (default: high).",
        ),
    ] = "high",
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--media-dir",
            help="Directory to save rendered video output.",
        ),
    ] = None,
    fps: Annotated[
        int | None,
        typer.Option(
            "--fps",
            help="Override frame rate (e.g. 30, 60). Defaults to preset fps.",
        ),
    ] = None,
    open_after: Annotated[
        bool,
        typer.Option(
            "--open",
            help="Open the rendered video after completion.",
        ),
    ] = False,
    skip_validate: Annotated[
        bool,
        typer.Option(
            "--skip-validate",
            help="Skip scientific defensibility validation before render.",
        ),
    ] = False,
):
    """Compile and render a scientific animation at the chosen quality preset.

    Quality presets (pixel size / fps):
      preview  → 480p / 30 fps   (fast iteration)
      medium   → 720p / 30 fps
      high     → 1080p / 60 fps  (default – publication ready)
      ultra    → 1440p / 60 fps
      4k       → 2160p / 60 fps  (very slow, for final mastering)
    """
    preset = _QUALITY_PRESETS.get(quality.lower())
    if preset is None:
        console.print(
            f"[bold red]Unknown quality '{quality}'. "
            f"Choose from: {', '.join(_QUALITY_PRESETS)}[/bold red]"
        )
        raise typer.Exit(code=1)

    manim_flag, _w, _h, default_fps = preset
    target_fps = fps or default_fps

    with open(spec_path, encoding="utf-8") as f:
        yaml_content = f.read()

    raw_dict = yaml.safe_load(yaml_content)
    spec = ScientificSceneSpec.model_validate(raw_dict)

    # ── Scientific defensibility check before spending render time ──
    if not skip_validate:
        validator = DefensibilityValidator(strict=False)
        report = validator.validate(spec)
        if not report.is_defensible:
            console.print(
                f"[bold red][SVAS] Scene failed defensibility check "
                f"({len(report.errors)} error(s)). "
                f"Fix issues or re-run with --skip-validate.[/bold red]"
            )
            for issue in report.errors:
                console.print(f"  [red][FAIL] [{issue.rule_id}] {issue.message}[/red]")
            raise typer.Exit(code=1)
        elif report.warnings:
            console.print(
                f"[yellow][SVAS] {len(report.warnings)} pedagogical warning(s) – "
                f"scene is defensible but could be improved.[/yellow]"
            )

    # ── Compile DSL → Python ──
    sim_quality = "preview" if quality == "preview" else "final"
    py_code = ScientificCompiler.compile_yaml(yaml_content, quality=sim_quality)

    build_dir = Path.cwd() / ".motiongram_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    temp_script = build_dir / f"{spec.scene.id}.py"
    with open(temp_script, "w", encoding="utf-8") as f:
        f.write(py_code)

    class_name = f"Scene_{spec.scene.id}"

    cmd = [
        sys.executable, "-m", "manim",
        str(temp_script),
        class_name,
        manim_flag,
        "--fps", str(target_fps),
        "--disable_caching",  # always re-render cleanly
    ]
    # Inject custom resolution for presets that override (e.g. true 4K)
    if _w > 0 and _h > 0:
        cmd.extend(["--resolution", f"{_w},{_h}"])
    if output_dir:
        cmd.extend(["--media_dir", str(output_dir)])
    if open_after:
        cmd.append("--open")

    console.print(
        f"[bold cyan]MotionGram Sci Render[/bold cyan] "
        f"[dim]{spec.scene.id}[/dim] "
        f"[green]{quality.upper()}[/green] "
        f"@ [yellow]{target_fps}fps[/yellow]"
    )
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        console.print(
            f"[bold red]Manim render failed with code {result.returncode}[/bold red]"
        )
        raise typer.Exit(code=result.returncode)
    console.print(
        f"[bold green][OK] Rendered {spec.scene.id} "
        f"({quality.upper()} @ {target_fps}fps)[/bold green]"
    )


@sci_app.command(name="validate")
def validate_command(
    spec_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to scientific scene YAML specification.",
        ),
    ],
    domain: Annotated[
        str | None,
        typer.Option(
            "--domain",
            "-d",
            help="Explicit scientific domain (e.g. dynamical_systems, linear_algebra, vector_calculus).",
        ),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Fail on pedagogical warnings as well as hard errors.",
        ),
    ] = False,
):
    """Validate that a scientific animation spec is scientifically defensible and pedagogically sound."""
    with open(spec_path, encoding="utf-8") as f:
        yaml_content = f.read()

    try:
        raw_dict = yaml.safe_load(yaml_content)
        spec = ScientificSceneSpec.model_validate(raw_dict)
    except Exception as exc:
        console.print(f"[bold red]Specification schema validation failed:[/bold red] {exc}")
        raise typer.Exit(code=1)

    validator = DefensibilityValidator(strict=strict)
    report = validator.validate(spec, domain=domain)

    table = Table(title=f"Scientific Defensibility Audit: {spec.scene.id} (Template: {spec.scene.template})")
    table.add_column("Rule ID", style="cyan", no_wrap=True)
    table.add_column("Domain", style="magenta")
    table.add_column("Severity", style="bold")
    table.add_column("Message", style="white")
    table.add_column("Remediation", style="dim")

    for issue in report.issues:
        sev_style = "red" if issue.severity == "error" else "yellow"
        table.add_row(
            issue.rule_id,
            issue.domain,
            f"[{sev_style}]{issue.severity.upper()}[/{sev_style}]",
            issue.message,
            issue.remediation,
        )

    if report.issues:
        console.print(table)
    else:
        console.print(f"[bold green][PASS] Scene '{spec.scene.id}' passed all scientific defensibility checks.[/bold green]")

    if not report.is_defensible:
        console.print(
            f"\n[bold red][FAIL] Scene is not scientifically defensible ({len(report.errors)} error(s), {len(report.warnings)} warning(s)).[/bold red]"
        )
        raise typer.Exit(code=1)
    else:
        if report.warnings:
            console.print(
                f"\n[yellow]Scene is defensible with {len(report.warnings)} pedagogical warning(s). Run with --strict to enforce warnings.[/yellow]"
            )
        else:
            console.print("\n[bold green]Defensibility status: FULLY SOUND AND DEFENSIBLE.[/bold green]")

"""Command-line interface for ManimGram Slides."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml

from motiongram.slides.assembler import build_deck, render_deck_slides
from motiongram.slides.compiler import compile_deck
from motiongram.slides.schema import DeckSpec
from motiongram.slides.validation import validate_deck

slides_app = typer.Typer(
    name="slides",
    help="ManimGram Slides — Declarative narrated presentations with ManimCE.",
    no_args_is_help=True,
)


def _load_deck(spec_file: Path) -> DeckSpec:
    """Load and validate DeckSpec YAML or JSON file."""
    content = spec_file.read_text(encoding="utf-8")
    raw = yaml.safe_load(content)
    if "deck" in raw and isinstance(raw["deck"], dict):
        raw = raw["deck"]
    deck = DeckSpec.model_validate(raw)
    is_valid, errors, warnings = validate_deck(deck)
    for w in warnings:
        typer.secho(f"[WARN] {w}", fg=typer.colors.YELLOW)
    if not is_valid:
        typer.secho("[ERROR] Deck validation failed:", fg=typer.colors.RED, err=True)
        for e in errors:
            typer.secho(f"  - {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    return deck


@slides_app.command("compile")
def slides_compile(
    spec_file: Annotated[
        Path,
        typer.Argument(help="Path to DeckSpec YAML/JSON file", exists=True, readable=True),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Target directory for generated scripts"),
    ] = None,
) -> None:
    """Compile a DeckSpec YAML into individual ManimCE VoiceoverScene Python scripts."""
    deck = _load_deck(spec_file)
    typer.echo(f"Compiling deck '{deck.id}' ({len(deck.slides)} slides)...")
    try:
        scripts = compile_deck(deck, output_dir)
        msg = f"[OK] Generated {len(scripts)} slide scenes under: {scripts[0].parent}"
        typer.secho(msg, fg=typer.colors.GREEN)
        for s in scripts:
            typer.echo(f"  - {s.name}")
    except Exception as e:
        typer.secho(f"[ERROR] Compilation failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e


@slides_app.command("render")
def slides_render(
    spec_file: Annotated[
        Path,
        typer.Argument(help="Path to DeckSpec YAML/JSON file", exists=True, readable=True),
    ],
    slide_id: Annotated[
        str | None,
        typer.Option("--slide", "-s", help="Render only a specific slide ID"),
    ] = None,
    quality: Annotated[
        str,
        typer.Option("--quality", "-q", help="Render quality (ql, qm, qh, qk)"),
    ] = "ql",
    still: Annotated[
        bool,
        typer.Option("--still", help="Render keyframe layout still images instead of video"),
    ] = False,
    cache: Annotated[
        bool,
        typer.Option("--cache/--no-cache", help="Enable/disable content-addressed caching"),
    ] = True,
    ultra_fast: Annotated[
        bool,
        typer.Option("--ultra-fast", help="Render at 640x360@10fps for ultra-fast previews"),
    ] = False,
) -> None:
    """Render compiled slides with caching and diagnostic error reporting."""
    deck = _load_deck(spec_file)
    base_dir = Path(f"output/decks/{deck.id}")
    scripts = compile_deck(deck, base_dir)

    if slide_id:
        scripts = [s for s in scripts if slide_id in s.stem]
        if not scripts:
            err = f"[ERROR] Slide '{slide_id}' not found in deck."
            typer.secho(err, fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

    typer.echo(f"Rendering {len(scripts)} slide(s)...")
    try:
        artifacts = render_deck_slides(
            slide_scripts=scripts,
            quality=quality,
            still=still,
            use_cache=cache,
            output_dir=base_dir / "media",
            ultra_fast=ultra_fast,
        )
        for a in artifacts:
            typer.secho(f"[OK] Artifact ready: {a}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"[ERROR] Render failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e


@slides_app.command("build")
def slides_build(
    spec_file: Annotated[
        Path,
        typer.Argument(help="Path to DeckSpec YAML/JSON file", exists=True, readable=True),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Path for final presentation MP4"),
    ] = None,
    quality: Annotated[
        str,
        typer.Option("--quality", "-q", help="Render quality (ql, qm, qh, qk)"),
    ] = "ql",
    cache: Annotated[
        bool,
        typer.Option("--cache/--no-cache", help="Enable/disable content-addressed caching"),
    ] = True,
    ultra_fast: Annotated[
        bool,
        typer.Option("--ultra-fast", help="Use 640x360@10fps for quick deck previews"),
    ] = False,
) -> None:
    """End-to-end presentation build: compile, render with cache, and assemble final MP4."""
    deck = _load_deck(spec_file)
    typer.echo(f"Building complete deck '{deck.id}' ({len(deck.slides)} slides)...")
    try:
        final_mp4 = build_deck(
            deck=deck,
            quality=quality,
            output_file=output,
            use_cache=cache,
            ultra_fast=ultra_fast,
        )
        typer.secho(f"[OK] Full presentation assembled at: {final_mp4}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"[ERROR] Build failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e


@slides_app.command("schema")
def slides_schema(
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output path for JSON Schema"),
    ] = None,
) -> None:
    """Export JSON Schema for DeckSpec (for LLM tool-calling and constrained decoding)."""
    schema_dict = DeckSpec.model_json_schema()
    schema_str = json.dumps(schema_dict, indent=2)
    if output:
        output.write_text(schema_str, encoding="utf-8")
        typer.secho(f"[OK] Schema written to: {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(schema_str)

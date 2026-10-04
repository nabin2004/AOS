"""Command-line interface for MotionGram."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Annotated

import typer

from motiongram.core import Scene
from motiongram.sci.cli import sci_app
from motiongram.slides.cli import slides_app

app = typer.Typer(
    no_args_is_help=True,
    help="MotionGram — The grammar of motion graphics.",
)


@app.command("backends")
def list_backends() -> None:
    """List named render targets (ASCII terminal vs Skia frame buffer)."""

    typer.echo("ascii — motiongram.Renderer (terminal grid)")
    typer.echo("skia  — motiongram.SkiaRenderer (RGBA ndarray via skia-python)")


def _import_scene_module(scene_file: Path) -> ModuleType:
    """Load ``scene_file`` as a module (``_user_scene``)."""
    spec = importlib.util.spec_from_file_location("_user_scene", str(scene_file))
    if spec is None or spec.loader is None:
        raise typer.BadParameter(f"Cannot load module from {scene_file}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_user_scene"] = mod
    spec.loader.exec_module(mod)
    return mod


def _scene_from_module(mod: ModuleType, scene_file: Path) -> Scene:
    """Return a :class:`~motiongram.core.Scene` from a loaded user module.

    Looks for (in order):

    1. ``build_scene()`` callable
    2. Module-level ``scene``
    """

    if hasattr(mod, "build_scene") and callable(mod.build_scene):
        obj = mod.build_scene()
        if isinstance(obj, Scene):
            return obj
        raise typer.BadParameter("build_scene() did not return a Scene instance")

    if hasattr(mod, "scene") and isinstance(mod.scene, Scene):
        return mod.scene

    raise typer.BadParameter(
        f"No build_scene() function or 'scene' attribute found in {scene_file}"
    )


@app.command()
def render(
    scene_file: Annotated[
        Path,
        typer.Argument(help="Path to scene .py or .yaml", exists=True, readable=True),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output MP4 path (default: <scene_name>.mp4)"),
    ] = None,
    width: Annotated[
        int | None,
        typer.Option(help="Override scene width"),
    ] = None,
    height: Annotated[
        int | None,
        typer.Option(help="Override scene height"),
    ] = None,
    fps: Annotated[
        float | None,
        typer.Option(help="Override scene FPS"),
    ] = None,
    frames_dir: Annotated[
        Path | None,
        typer.Option(
            "--frames-dir",
            help="Write each frame as PNG under this directory (same pass as MP4)",
        ),
    ] = None,
    audio: Annotated[
        Path | None,
        typer.Option("--audio", "-a", help="Path to audio file to mux into video"),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress progress output"),
    ] = False,
) -> None:
    """Render a scene file to MP4 video."""
    from motiongram.export import PyAVEncoder
    from motiongram.render import SkiaRenderer

    linear_timeline = False
    suffix = scene_file.suffix.lower()
    audio_path = audio

    if suffix in (".yaml", ".yml"):
        from motiongram.manifest.loader import render_manifest

        program, scene = render_manifest(scene_file)
        if output is None:
            output = program.output_path
        renderer = SkiaRenderer(clear_color=program.clear_color)
        linear_timeline = program.uses_custom_easing
        if program.voiceover_paths and audio_path is None:
            if len(program.voiceover_paths) == 1:
                audio_path = program.voiceover_paths[0]
            else:
                from motiongram.audio.mixer import AudioMixer
                mixer = AudioMixer()
                build_dir = Path(".motiongram_build")
                build_dir.mkdir(parents=True, exist_ok=True)
                audio_path = mixer.concatenate(
                    program.voiceover_paths,
                    build_dir / f"{scene_file.stem}_mixed.wav",
                )
    else:
        mod = _import_scene_module(scene_file)
        scene = _scene_from_module(mod, scene_file)
        if output is None:
            output = Path(scene_file.stem + ".mp4")
        get_renderer = getattr(mod, "get_skia_renderer", None)
        renderer = (
            get_renderer()
            if callable(get_renderer)
            else SkiaRenderer()
        )

    if width is not None:
        scene.width = width
    if height is not None:
        scene.height = height
    if fps is not None:
        scene.fps = fps

    encoder = PyAVEncoder(
        scene=scene,
        output_path=output,
        renderer=renderer,
        frames_dir=frames_dir,
        linear_timeline=linear_timeline,
        audio_path=audio_path,
    )
    result = encoder.encode(verbose=not quiet)
    msg = f"Rendered: {result} ({result.stat().st_size:,} bytes)"
    if frames_dir is not None:
        msg += f"; frames: {frames_dir.expanduser().resolve()}"
    typer.echo(msg)



@app.command()
def preview(
    scene_file: Annotated[
        Path,
        typer.Argument(help="Path to YAML manifest", exists=True, readable=True),
    ],
    port: Annotated[
        int,
        typer.Option("--port", help="HTTP port for preview server"),
    ] = 8765,
    host: Annotated[
        str,
        typer.Option("--host", help="Bind address"),
    ] = "127.0.0.1",
    time: Annotated[
        str,
        typer.Option("--time", help="Initial scrub time (e.g. 0s, 2.5)"),
    ] = "0s",
    video_on_save: Annotated[
        bool,
        typer.Option(
            "--video-on-save",
            help="Background full MP4 encode after saves (debounced)",
        ),
    ] = False,
) -> None:
    """Live-preview a YAML manifest in the browser (reloads on save)."""
    suffix = scene_file.suffix.lower()
    if suffix not in (".yaml", ".yml"):
        raise typer.BadParameter("preview only supports .yaml / .yml manifests")

    from motiongram.preview import run_preview_server

    run_preview_server(
        scene_file,
        host=host,
        port=port,
        video_on_save=video_on_save,
        initial_time=time,
    )


# --- ManimGram (DSL to ManimCE Transpiler) ---

manimgram_app = typer.Typer(
    no_args_is_help=True,
    help="ManimGram - Declarative DSL transpiler for ManimCE.",
)


@manimgram_app.command("compile")
def manim_compile(
    spec_file: Annotated[
        Path,
        typer.Argument(
            help="Path to ManimGram YAML or JSON specification",
            exists=True,
            readable=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output .py file path (default: <spec_file>.py)"),
    ] = None,
) -> None:
    """Compile a declarative YAML/JSON DSL specification into a ManimCE Python script."""
    from motiongram.manimgram.compiler import compile_file

    try:
        out_path = compile_file(spec_file, output)
        typer.secho(f"[OK] Compiled successfully to: {out_path}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"[ERROR] Compilation failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e


@manimgram_app.command("render")
def manim_render(
    spec_file: Annotated[
        Path,
        typer.Argument(
            help="Path to ManimGram YAML/JSON specification or compiled .py file",
            exists=True,
            readable=True,
        ),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option("--media-dir", "-m", help="Directory for rendered video"),
    ] = None,
    quality: Annotated[
        str,
        typer.Option("--quality", "-q", help="Render quality (ql, qm, qh, qk)"),
    ] = "ql",
    preview: Annotated[
        bool,
        typer.Option("--preview", "-p", help="Open video player automatically after render"),
    ] = False,
    still: Annotated[
        bool,
        typer.Option("--still", "-s", help="Render a still layout image instead of full video"),
    ] = False,
    cache: Annotated[
        bool,
        typer.Option("--cache/--no-cache", help="Enable/disable content-addressed caching"),
    ] = True,
    cache_dir: Annotated[
        Path | None,
        typer.Option("--cache-dir", help="Directory for cached artifacts"),
    ] = None,
    ultra_fast: Annotated[
        bool,
        typer.Option("--ultra-fast", help="Use 640x360 at 10fps for ultra-fast preview"),
    ] = False,
) -> None:
    """Compile (if YAML/JSON) and render a scene with ManimCE (with layered caching)."""
    from motiongram.manimgram.compiler import compile_file
    from motiongram.manimgram.runner import render_scene

    raw_spec_content: str | None = None
    script_path = spec_file
    if spec_file.suffix.lower() in (".yaml", ".yml", ".json"):
        raw_spec_content = spec_file.read_text(encoding="utf-8")
        typer.echo(f"Compiling {spec_file} to Manim script...")
        try:
            script_path = compile_file(spec_file)
            typer.secho(f"[OK] Compiled: {script_path}", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"[ERROR] Compilation failed: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from e

    mode_label = "still image" if still else ("ultra-fast preview" if ultra_fast else f"-{quality}")
    typer.echo(f"Rendering with ManimCE ({mode_label})...")

    custom_res = (640, 360) if ultra_fast else None
    fps = 10.0 if ultra_fast else None

    result = render_scene(
        script_path=script_path,
        quality=quality,
        preview=preview,
        output_dir=output_dir,
        still=still,
        use_cache=cache,
        cache_dir=cache_dir,
        spec_content=raw_spec_content,
        custom_res=custom_res,
        fps=fps,
    )

    if not result.success:
        err_header = f"[ERROR] Render failed (exit code {result.exit_code}):"
        typer.secho(err_header, fg=typer.colors.RED, err=True)
        if result.error_summary:
            typer.secho(f"  Diagnostic: {result.error_summary}", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=result.exit_code)

    if result.cached:
        msg = "[CACHE HIT] Instant artifact retrieved from cache (zero render time!)"
        typer.secho(msg, fg=typer.colors.CYAN)

    if result.image_path:
        typer.secho(f"[OK] Still layout ready at: {result.image_path}", fg=typer.colors.GREEN)
    elif result.video_path:
        typer.secho(f"[OK] Video ready at: {result.video_path}", fg=typer.colors.GREEN)
    else:
        typer.secho("[OK] Scene rendered successfully.", fg=typer.colors.GREEN)


@manimgram_app.command("schema")
def manim_schema(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Output path to save JSON schema (default: print to stdout)"
        ),
    ] = None,
) -> None:
    """Output JSON Schema for ManimGram DSL (for LLM tool-calling/constrained decoding)."""
    from motiongram.manimgram.llm import get_json_schema_str

    schema_str = get_json_schema_str()
    if output is not None:
        output.write_text(schema_str, encoding="utf-8")
        typer.secho(f"[OK] Schema saved to: {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(schema_str)


@manimgram_app.command("repair")
def manim_repair(
    spec_file: Annotated[
        Path,
        typer.Argument(
            help="Path to invalid or failing ManimGram YAML/JSON specification",
            exists=True,
            readable=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output path for the generated repair prompt"),
    ] = None,
) -> None:
    """Validate a specification and generate a structured repair prompt if invalid."""
    from motiongram.manimgram.llm import validate_and_generate_repair

    content = spec_file.read_text(encoding="utf-8")
    is_valid, msg = validate_and_generate_repair(content)
    if is_valid:
        typer.secho(f"[OK] {spec_file} is valid ManimGram YAML/JSON.", fg=typer.colors.GREEN)
        return

    warn_msg = f"[WARN] Validation failed for {spec_file}. Generated repair prompt:\n"
    typer.secho(warn_msg, fg=typer.colors.YELLOW)
    if output is not None:
        output.write_text(msg, encoding="utf-8")
        typer.secho(f"[OK] Repair prompt written to: {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(msg)


# Register sub-app under both 'manim' and 'manimgram'
app.add_typer(manimgram_app, name="manim")
app.add_typer(manimgram_app, name="manimgram")

# Register 'slides' sub-app for presentation decks
app.add_typer(slides_app, name="slides")

# Register 'sci' sub-app for scientific simulation and animation
app.add_typer(sci_app, name="sci")


def main() -> None:
    """Entry point for ``python -m motiongram`` style invocation."""
    app()


if __name__ == "__main__":
    main()


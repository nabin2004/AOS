from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ir.manim_ir import RenderConfig
from pydantic_ai import RunContext

from tools.deps import QUALITY_TO_MANIM_FLAG, ToolDeps
from tools.registry import aos_toolset

# manim's --format only produces a single video container per invocation; the
# IR also allows "png_sequence" (a full per-frame image dump), which the CLI
# has no single-flag equivalent for, so it is rejected explicitly rather than
# silently mis-rendered as something else.
UNSUPPORTED_OUTPUT_FORMATS = {"png_sequence"}

OUTPUT_EXTENSIONS = {
    "mp4": "mp4",
    "mov": "mov",
    "gif": "gif",
}


def _docker_volume_path(path: Path) -> str:
    """Normalize a host path for Docker volume mounts (Windows-friendly)."""
    resolved = path.resolve()
    return str(resolved).replace("\\", "/")


def _parse_output_path(log: str, workspace: Path, extension: str) -> str:
    """Extract rendered media path from Manim stdout for the given container extension."""
    ext = re.escape(extension)
    patterns = [
        r"File ready at ['\"]([^'\"]+)['\"]",
        rf"Rendered .*?\n.*?([^\n]+\.{ext})",
        rf"(media/videos/[^\s]+\.{ext})",
    ]
    for pattern in patterns:
        match = re.search(pattern, log, re.IGNORECASE)
        if match:
            candidate = Path(match.group(1))
            if candidate.is_absolute():
                return str(candidate)
            return str((workspace / candidate).resolve())
    return ""


def _build_render_command(
    scene_file: str,
    scene_class: str,
    render_config: RenderConfig,
    image: str,
    volume: str,
) -> list[str]:
    if render_config.output_format in UNSUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"output_format {render_config.output_format!r} has no single-command "
            "manim CLI equivalent; use 'mp4', 'mov', or 'gif' instead."
        )

    quality_flag = QUALITY_TO_MANIM_FLAG[render_config.quality]
    width, height = render_config.resolution

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{volume}:/manim",
        image,
        "manim",
        f"-q{quality_flag}",
        "--fps",
        str(render_config.fps),
        "-r",
        f"{width},{height}",
        "--format",
        render_config.output_format,
    ]
    if render_config.transparent:
        cmd.append("--transparent")
    cmd += [scene_file, scene_class]
    return cmd


@aos_toolset.tool
def render_manim_scene(
    ctx: RunContext[ToolDeps],
    scene_file: str,
    scene_class: str,
    render_config_json: str | None = None,
) -> str:
    """Render a Manim scene file via Docker and return success/output path/log JSON.

    Requires Docker Desktop with the ``manimcommunity/manim`` image available.
    The workspace directory is mounted at ``/manim`` inside the container.

    Args:
        scene_file: Python filename relative to workspace (e.g. ``lecture.py``).
        scene_class: Manim Scene class name to render.
        render_config_json: JSON for an IR ``RenderConfig`` (quality, fps,
            resolution, output_format, transparent). Defaults to
            ``RenderConfig()`` (high quality, 60fps, 1920x1080, mp4) when omitted.
    """
    workspace = ctx.deps.workspace_dir.resolve()
    scene_path = workspace / scene_file
    if not scene_path.exists():
        raise ValueError(f"scene file not found: {scene_path}")

    render_config = (
        RenderConfig.model_validate_json(render_config_json)
        if render_config_json
        else RenderConfig()
    )

    volume = _docker_volume_path(workspace)
    cmd = _build_render_command(
        scene_file, scene_class, render_config, ctx.deps.docker_image, volume
    )

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workspace,
            timeout=600,
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "Docker not found. Install Docker Desktop and pull manimcommunity/manim."
        ) from exc
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "output_path": "", "log": "Render timed out after 600s."})

    extension = OUTPUT_EXTENSIONS.get(render_config.output_format, render_config.output_format)
    log = proc.stdout + proc.stderr
    output_path = _parse_output_path(log, workspace, extension)
    success = proc.returncode == 0 and bool(output_path)

    return json.dumps({"success": success, "output_path": output_path, "log": log})

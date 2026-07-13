from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# `docker run` pays for a fresh container filesystem/network namespace on
# every invocation; on Docker Desktop that overhead can rival or exceed the
# render itself for short scenes. We instead keep one idle container per
# workspace alive (`tail -f /dev/null`) and shell into it with `docker exec`,
# which skips that setup entirely. See README.md "Manim render performance".
_CONTAINER_PREFIX = "aos-manim-"
_CONTAINER_LOCKS: dict[str, threading.Lock] = {}
_SUBPROCESS_KWARGS = {"text": True, "encoding": "utf-8", "errors": "replace"}


def _docker_volume_path(path: Path) -> str:
    """Normalize a host path for Docker volume mounts (Windows-friendly)."""
    resolved = path.resolve()
    return str(resolved).replace("\\", "/")


def _container_name(volume: str, image: str) -> str:
    digest = hashlib.sha1(f"{image}:{volume}".encode()).hexdigest()[:16]
    return f"{_CONTAINER_PREFIX}{digest}"


def _container_lock(name: str) -> threading.Lock:
    if name not in _CONTAINER_LOCKS:
        _CONTAINER_LOCKS[name] = threading.Lock()
    return _CONTAINER_LOCKS[name]


def _ensure_container(image: str, volume: str, name: str) -> None:
    """Start (or resume) the long-lived render container for this workspace."""
    with _container_lock(name):
        inspect = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True,
            **_SUBPROCESS_KWARGS,
        )
        if inspect.returncode == 0:
            if (inspect.stdout or "").strip() != "true":
                subprocess.run(
                    ["docker", "start", name],
                    capture_output=True,
                    **_SUBPROCESS_KWARGS,
                    check=True,
                )
            return

        run = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-v",
                f"{volume}:/manim",
                image,
                "tail",
                "-f",
                "/dev/null",
            ],
            capture_output=True,
            **_SUBPROCESS_KWARGS,
        )
        stderr = run.stderr or ""
        if run.returncode != 0 and "already in use" not in stderr:
            raise RuntimeError(f"failed to start render container: {stderr}")

        if run.returncode != 0:
            inspect = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", name],
                capture_output=True,
                **_SUBPROCESS_KWARGS,
            )
            if inspect.returncode != 0:
                raise RuntimeError(f"render container {name} missing after create race")
            if (inspect.stdout or "").strip() != "true":
                subprocess.run(
                    ["docker", "start", name],
                    capture_output=True,
                    **_SUBPROCESS_KWARGS,
                    check=True,
                )


def _normalize_manim_output_path(raw: str, workspace: Path) -> Path:
    """Map Manim log paths (including container /manim/ prefixes) to host workspace paths."""
    normalized = raw.replace("\\", "/")
    if normalized.startswith("/manim/"):
        normalized = normalized.removeprefix("/manim/")
    elif normalized.startswith("manim/"):
        normalized = normalized.removeprefix("manim/")

    candidate = Path(normalized)
    if candidate.is_absolute() and candidate.exists():
        return candidate.resolve()
    return (workspace / candidate).resolve()


def _discover_output_path(workspace: Path, scene_class: str, extension: str) -> str:
    """Find the newest rendered file for a scene when Manim logs omit the path."""
    matches = sorted(
        workspace.glob(f"media/videos/**/{scene_class}.{extension}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if matches:
        return str(matches[0].resolve())
    return ""


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
            return str(_normalize_manim_output_path(match.group(1), workspace))
    return ""


def _manim_args(
    scene_file: str,
    scene_class: str,
    render_config: RenderConfig,
) -> list[str]:
    if render_config.output_format in UNSUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"output_format {render_config.output_format!r} has no single-command "
            "manim CLI equivalent; use 'mp4', 'mov', or 'gif' instead."
        )

    quality_flag = QUALITY_TO_MANIM_FLAG[render_config.quality]
    width, height = render_config.resolution

    args = [
        "manim",
        f"-q{quality_flag}",
        "--fps",
        str(render_config.fps),
        "-r",
        f"{width},{height}",
        "--format",
        render_config.output_format,
        # WARNING-level logging avoids per-frame progress-bar/log overhead
        # and keeps stdout small enough that _parse_output_path stays cheap.
        "-v",
        "WARNING",
    ]
    if render_config.transparent:
        args.append("--transparent")
    args += [scene_file, scene_class]
    return args


def _build_render_command(
    scene_file: str,
    scene_class: str,
    render_config: RenderConfig,
    image: str,
    volume: str,
    container_name: str | None,
) -> list[str]:
    args = _manim_args(scene_file, scene_class, render_config)
    if container_name is not None:
        return ["docker", "exec", "-w", "/manim", container_name] + args
    return ["docker", "run", "--rm", "-w", "/manim", "-v", f"{volume}:/manim", image] + args


def _render_one(
    deps: ToolDeps,
    scene_file: str,
    scene_class: str,
    render_config: RenderConfig,
) -> dict:
    workspace = deps.workspace_dir.resolve()
    scene_path = workspace / scene_file
    if not scene_path.exists():
        raise ValueError(f"scene file not found: {scene_path}")

    volume = _docker_volume_path(workspace)
    container_name = None
    if deps.persistent_container:
        container_name = _container_name(volume, deps.docker_image)
        _ensure_container(deps.docker_image, volume, container_name)

    cmd = _build_render_command(
        scene_file, scene_class, render_config, deps.docker_image, volume, container_name
    )

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            cwd=workspace,
            timeout=600,
            **_SUBPROCESS_KWARGS,
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "Docker not found. Install Docker Desktop and pull manimcommunity/manim."
        ) from exc
    except subprocess.TimeoutExpired:
        return {"success": False, "output_path": "", "log": "Render timed out after 600s."}

    extension = OUTPUT_EXTENSIONS.get(render_config.output_format, render_config.output_format)
    log = (proc.stdout or "") + (proc.stderr or "")
    output_path = _parse_output_path(log, workspace, extension)
    if not output_path and proc.returncode == 0:
        output_path = _discover_output_path(workspace, scene_class, extension)
    success = proc.returncode == 0 and bool(output_path)

    return {"success": success, "output_path": output_path, "log": log}


def render_scenes_for_deps(
    deps: ToolDeps,
    scene_file: str,
    scene_classes: list[str],
    render_config: RenderConfig | None = None,
) -> dict[str, dict]:
    """Render several scenes concurrently without a pydantic-ai RunContext."""
    config = render_config or RenderConfig()
    max_workers = min(len(scene_classes), os.cpu_count() or 4) or 1
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_render_one, deps, scene_file, scene_class, config): scene_class
            for scene_class in scene_classes
        }
        for future in as_completed(futures):
            scene_class = futures[future]
            try:
                results[scene_class] = future.result()
            except Exception as exc:  # noqa: BLE001 - surfaced per-scene, not raised
                results[scene_class] = {"success": False, "output_path": "", "log": str(exc)}
    return results


def _render_failure_snippet(log: str, max_len: int = 120) -> str:
    for line in log.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Manim Community"):
            continue
        if "ERROR" in stripped or "Error" in stripped or "Traceback" in stripped:
            return stripped[:max_len]
    for line in log.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("Manim Community"):
            return stripped[:max_len]
    return "unknown error"


def summarize_render_results(results: dict[str, dict]) -> dict:
    """Return attempted/succeeded/failed counts and per-scene failure snippets."""
    succeeded = sum(1 for r in results.values() if r.get("success"))
    failed = len(results) - succeeded
    failures = [
        (scene_class, _render_failure_snippet(result.get("log", "")))
        for scene_class, result in sorted(results.items())
        if not result.get("success")
    ]
    return {
        "attempted": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "failures": failures,
    }


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
    By default renders run in a reused per-workspace container (``docker
    exec``) instead of a fresh ``docker run`` each time, to cut per-call
    container-startup overhead. Set ``ToolDeps.persistent_container=False``
    to fall back to a one-off ``docker run --rm`` per call.

    Args:
        scene_file: Python filename relative to workspace (e.g. ``lecture.py``).
        scene_class: Manim Scene class name to render.
        render_config_json: JSON for an IR ``RenderConfig`` (quality, fps,
            resolution, output_format, transparent). Defaults to
            ``RenderConfig()`` (high quality, 60fps, 1920x1080, mp4) when omitted.
    """
    render_config = (
        RenderConfig.model_validate_json(render_config_json)
        if render_config_json
        else RenderConfig()
    )
    result = _render_one(ctx.deps, scene_file, scene_class, render_config)
    return json.dumps(result)


@aos_toolset.tool
def render_manim_scenes(
    ctx: RunContext[ToolDeps],
    scene_file: str,
    scene_classes: list[str],
    render_config_json: str | None = None,
) -> str:
    """Render several Manim scenes from the same file concurrently.

    Manim/Cairo rendering is single-threaded per scene, so a lecture with
    many independent scenes renders fastest by fanning them out across CPU
    cores rather than one at a time. This runs one ``manim`` process per
    scene (via ``docker exec`` into the shared per-workspace container,
    bounded by CPU count) and returns a JSON map of
    ``{scene_class: {success, output_path, log}}``.

    Args:
        scene_file: Python filename relative to workspace (e.g. ``lecture.py``).
        scene_classes: Manim Scene class names to render, from that file.
        render_config_json: JSON for an IR ``RenderConfig``, applied to every
            scene. Defaults to ``RenderConfig()`` when omitted.
    """
    render_config = (
        RenderConfig.model_validate_json(render_config_json)
        if render_config_json
        else RenderConfig()
    )

    results = render_scenes_for_deps(
        ctx.deps, scene_file, scene_classes, render_config=render_config
    )
    return json.dumps(results)

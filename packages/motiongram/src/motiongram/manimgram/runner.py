"""Execution runner and diagnostic extractor for Manim scenes with layered caching."""

from __future__ import annotations

import contextlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from motiongram.manimgram.cache import (
    compute_cache_key,
    get_cached_entry,
    store_cached_entry,
)


@dataclass
class RenderResult:
    """Outcome of a Manim render execution."""
    success: bool
    exit_code: int
    video_path: Path | None = None
    image_path: Path | None = None
    cached: bool = False
    manifest_path: Path | None = None
    stdout: str = ""
    stderr: str = ""
    error_summary: str | None = None


def extract_error_diagnostic(stderr: str, stdout: str) -> str:
    """Parse stderr and stdout to identify the failure cause (LaTeX, selector, syntax, etc.)."""
    full_output = f"{stdout}\n{stderr}"

    if "LaTeX Error" in full_output or "latex error" in full_output.lower():
        # Match latex error snippet
        m = re.search(r"! (.*?)(?:\nl\.\d+.*?)?", full_output)
        if m:
            return f"LaTeX Compilation Error: {m.group(1).strip()}"
        return "LaTeX Compilation Error: Please verify LaTeX syntax in MathTex/Tex."

    if "IndexError" in full_output:
        return (
            "Submobject Index Error: "
            "Attempted to access an out-of-bounds submobject index or selector."
        )

    if "KeyError" in full_output:
        m = re.search(r"KeyError:\s*(.*)", full_output)
        return f"Key Error: {m.group(1) if m else 'missing key'}"

    if "NameError" in full_output:
        m = re.search(r"NameError:\s*(.*)", full_output)
        return f"Name Error: {m.group(1) if m else 'unresolved identifier'}"

    # Extract final exception line if present
    trace_lines = [line.strip() for line in full_output.splitlines() if line.strip()]
    for line in reversed(trace_lines):
        if any(err in line for err in ("Error:", "Exception:")):
            return line

    return "Unknown Render Error. Check full execution log for details."


def extract_artifact_path(
    stdout: str, extension: str, search_dir: Path | None = None
) -> Path | None:
    """Extract artifact path from Manim stdout or fallback to filesystem search."""
    # 1. Regex search handling multi-line wrapped path from Rich terminal logger
    pattern = rf"File ready at\s*['\"]?([\s\S]*?\.{extension})['\"]?"
    m = re.search(pattern, stdout, re.IGNORECASE)
    if m:
        lines = [line.strip() for line in m.group(1).splitlines()]
        clean = "".join(lines).strip("'\"")
        p = Path(clean)
        if p.is_file():
            return p

    # 2. Filesystem search fallback under media directory
    base_dir = search_dir or Path("media")
    target_sub = "images" if extension.lower() in ("png", "jpg", "jpeg") else "videos"
    search_path = base_dir / target_sub
    if search_path.is_dir():
        matches = sorted(
            search_path.glob(f"**/*.{extension}"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if matches and matches[0].is_file():
            return matches[0]

    return None


def render_scene(
    script_path: Path,
    scene_name: str | None = None,
    quality: str = "ql",
    preview: bool = False,
    output_dir: Path | None = None,
    still: bool = False,
    use_cache: bool = True,
    cache_dir: Path | None = None,
    spec_content: str | None = None,
    custom_res: tuple[int, int] | None = None,
    fps: float | None = None,
    seed: int = 42,
) -> RenderResult:
    """Execute manim CLI to render a compiled scene script with content-addressed caching."""
    script_path = Path(script_path)
    if not script_path.exists():
        return RenderResult(
            success=False,
            exit_code=1,
            error_summary=f"Script file '{script_path}' does not exist.",
        )

    effective_cache_dir = cache_dir or Path(".manim_cache")
    mode = "still" if still else "video"

    # 1. Content-addressed cache lookup (zero-cost render avoidance)
    cache_key: str | None = None
    if use_cache:
        raw_content = spec_content
        if raw_content is None:
            try:
                raw_content = script_path.read_text(encoding="utf-8")
            except Exception:
                raw_content = str(script_path)
        cache_key = compute_cache_key(
            spec_content=raw_content,
            quality=quality,
            mode=mode,
            custom_res=custom_res,
            fps=fps,
            seed=seed,
        )
        cached_entry = get_cached_entry(effective_cache_dir, cache_key)
        if cached_entry is not None:
            if cached_entry.artifact_type == "image":
                return RenderResult(
                    success=True,
                    exit_code=0,
                    image_path=cached_entry.artifact_path,
                    cached=True,
                    manifest_path=cached_entry.manifest_path,
                )
            return RenderResult(
                success=True,
                exit_code=0,
                video_path=cached_entry.artifact_path,
                cached=True,
                manifest_path=cached_entry.manifest_path,
            )

    # 2. Check if manim is available on PATH or via current Python interpreter
    manim_cmd = shutil.which("manim")
    base_cmd: list[str] | None = None
    if manim_cmd:
        base_cmd = [manim_cmd]
    else:
        import sys
        try:
            res = subprocess.run(
                [sys.executable, "-c", "import manim; print(manim.__version__)"],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                base_cmd = [sys.executable, "-m", "manim"]
        except Exception:
            base_cmd = None

    if not base_cmd:
        return RenderResult(
            success=False,
            exit_code=127,
            error_summary=(
                "Manim executable ('manim') not found on PATH or in current virtualenv. "
                "Please install manim via 'pip install manim'."
            ),
        )

    # 3. Build command: e.g. manim -ql script.py SceneName or manim -sql for stills
    if still:
        flag = f"-sp{quality}" if preview else f"-s{quality}"
    else:
        flag = f"-p{quality}" if preview else f"-{quality}"

    cmd = [*base_cmd, flag]
    if custom_res:
        cmd.extend(["-r", f"{custom_res[0]},{custom_res[1]}"])
    if fps:
        cmd.extend(["--fps", str(fps)])

    cmd.append(str(script_path))
    if scene_name:
        cmd.append(scene_name)

    if output_dir:
        cmd.extend(["--media_dir", str(output_dir)])

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if proc.returncode != 0:
        err_msg = extract_error_diagnostic(proc.stderr, proc.stdout)
        return RenderResult(
            success=False,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            error_summary=err_msg,
        )

    # 4. Search for produced video (.mp4) or still (.png) in output
    video_path: Path | None = None
    image_path: Path | None = None

    if still:
        image_path = extract_artifact_path(proc.stdout, "png", output_dir)
    else:
        video_path = extract_artifact_path(proc.stdout, "mp4", output_dir)

    # 5. Persist artifact into cache if enabled
    manifest_path: Path | None = None
    if use_cache and cache_key:
        active_artifact = image_path if still else video_path
        if active_artifact and active_artifact.is_file():
            script_text = None
            with contextlib.suppress(Exception):
                script_text = script_path.read_text(encoding="utf-8")
            stored = store_cached_entry(
                cache_dir=effective_cache_dir,
                cache_key=cache_key,
                source_artifact=active_artifact,
                artifact_type="image" if still else "video",
                script_content=script_text,
                extra_metadata={
                    "quality": quality,
                    "mode": mode,
                    "scene_name": scene_name,
                },
            )
            manifest_path = stored.manifest_path

    return RenderResult(
        success=True,
        exit_code=0,
        video_path=video_path,
        image_path=image_path,
        cached=False,
        manifest_path=manifest_path,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )

"""Stable entrypoints for UI/Celery/OpenCode: prompt → compiled MP4 path.

Returns a JSON-serializable dict so ``cli.py --json`` and subprocess callers
can parse a single stdout object.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


Mode = Literal["animate", "lecture"]


class VideoArtifact(BaseModel):
    ok: bool
    mode: Mode
    video_path: str | None = None
    scene_path: str | None = None
    run_dir: str | None = None
    scene_file: str | None = None
    has_audio: bool | None = None
    trajectory_path: str | None = None
    error: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


def find_mp4(
    root: str | Path | None,
    *,
    scene_name: str | None = None,
) -> Path | None:
    """Return the best final ``.mp4`` under ``root``, or None.

    Skips ``partial_movie_files``. Prefers a file whose stem matches
    ``scene_name`` when provided; otherwise picks the largest remaining MP4.
    """
    if root is None:
        return None
    base = Path(root)
    if not base.exists():
        return None
    if base.is_file() and base.suffix.lower() == ".mp4":
        return base

    preferred: list[Path] = []
    fallback: list[Path] = []
    for path in base.rglob("*.mp4"):
        if not path.is_file():
            continue
        if "partial_movie_files" in path.parts:
            continue
        if scene_name and path.stem == scene_name:
            preferred.append(path)
        else:
            fallback.append(path)

    pool = preferred or fallback
    if not pool:
        return None
    return max(pool, key=lambda p: p.stat().st_size)


def _resolve_scene_file(
    run_dir: str | Path | None,
    *,
    hint: str | None = None,
    lecture: bool = False,
) -> str | None:
    if hint:
        hint_path = Path(hint)
        if hint_path.is_file():
            return str(hint_path.resolve())
        if run_dir:
            candidate = Path(run_dir) / hint
            if candidate.is_file():
                return str(candidate.resolve())

    if run_dir is None:
        return None
    root = Path(run_dir)
    if not root.is_dir():
        return None

    if lecture:
        lecture_py = root / "lecture.py"
        if lecture_py.is_file():
            return str(lecture_py.resolve())

    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        scene_rel = manifest.get("scene_file")
        if scene_rel:
            scene_path = (
                Path(scene_rel) if Path(scene_rel).is_absolute() else root / scene_rel
            )
            if scene_path.is_file():
                return str(scene_path.resolve())

    py_files = sorted(
        p for p in root.glob("*.py") if p.is_file() and p.name != "__init__.py"
    )
    if len(py_files) == 1:
        return str(py_files[0].resolve())
    return None


def _manifest_has_audio(run_dir: str | Path | None) -> bool | None:
    if run_dir is None:
        return None
    manifest_path = Path(run_dir) / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    last = manifest.get("last_compile") or {}
    if "has_audio" in last:
        value = last.get("has_audio")
        if isinstance(value, bool) or value is None:
            return value
    if "has_audio" in manifest:
        value = manifest.get("has_audio")
        if isinstance(value, bool) or value is None:
            return value
    return None


def _trajectory_path(run_dir: str | Path | None) -> str | None:
    if run_dir is None:
        return None
    path = Path(run_dir) / "traces" / "trajectory.json"
    if path.is_file():
        return str(path.resolve())
    return None


def _compile_failure_error(result: dict[str, Any], run_dir: str | Path | None) -> str:
    """Prefer last_compile.failure_marker over stopped_reason=completed."""
    last: dict[str, Any] = {}
    if run_dir:
        manifest_path = Path(run_dir) / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                last = manifest.get("last_compile") or {}
            except (OSError, json.JSONDecodeError, TypeError):
                last = {}
    marker = last.get("failure_marker") or result.get("failure_marker")
    if marker:
        return str(marker)
    stopped = (result.get("stopped_reason") or "").strip()
    if stopped and stopped != "completed":
        return stopped
    return str(
        result.get("message")
        or last.get("message")
        # or "compile_failed"
    )


def _stage_output_dir(
    output_dir: str | Path,
    *,
    video_path: str | None,
    scene_path: str | None,
) -> dict[str, str]:
    """Copy final artifacts into ``output_dir``; return staged absolute paths."""
    dest = Path(output_dir).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    staged: dict[str, str] = {"output_dir": str(dest)}

    if video_path and Path(video_path).is_file():
        video_dest = dest / "final.mp4"
        shutil.copy2(video_path, video_dest)
        staged["video_path"] = str(video_dest)

    if scene_path and Path(scene_path).is_file():
        scene_dest = dest / Path(scene_path).name
        shutil.copy2(scene_path, scene_dest)
        staged["scene_path"] = str(scene_dest)

    return staged


async def run_animate(
    prompt: str,
    *,
    output_dir: str | Path | None = None,
) -> VideoArtifact:
    """Classify → plan → Manim coder/compile; resolve scene MP4."""
    from agent_graph import run_pipeline
    from openai_compatible import format_custom_endpoint_error

    try:
        result = await run_pipeline(prompt)
    except Exception as exc:
        return VideoArtifact(
            ok=False,
            mode="animate",
            error=format_custom_endpoint_error(str(exc)),
        )

    run_dir = result.get("run_dir")
    media_hint = result.get("media_hint")
    scene_name = result.get("scene_name")
    scene_file = _resolve_scene_file(run_dir, hint=result.get("scene_file"))
    has_audio = _manifest_has_audio(run_dir)
    trajectory_path = _trajectory_path(run_dir)

    if not result.get("compile_ok"):
        return VideoArtifact(
            ok=False,
            mode="animate",
            run_dir=run_dir,
            scene_file=scene_file,
            scene_path=scene_file,
            has_audio=has_audio,
            trajectory_path=trajectory_path,
            error=format_custom_endpoint_error(
                _compile_failure_error(result, run_dir)
            ),
            detail=result if isinstance(result, dict) else {},
        )

    manifest_video = None
    if run_dir:
        manifest_path = Path(run_dir) / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                last = manifest.get("last_compile") or {}
                candidate = last.get("video_path") or manifest.get("video_path")
                if candidate and Path(candidate).is_file():
                    manifest_video = Path(candidate)
            except (OSError, json.JSONDecodeError):
                pass

    mp4 = (
        manifest_video
        or find_mp4(media_hint, scene_name=scene_name)
        or find_mp4(run_dir, scene_name=scene_name)
    )
    if mp4 is None:
        return VideoArtifact(
            ok=False,
            mode="animate",
            run_dir=run_dir,
            scene_file=scene_file,
            scene_path=scene_file,
            has_audio=has_audio,
            trajectory_path=trajectory_path,
            error="compile_ok_but_no_mp4_found",
            detail=result if isinstance(result, dict) else {},
        )

    video_path = str(mp4.resolve())
    detail: dict[str, Any] = {
        "scene_name": scene_name,
        "stopped_reason": result.get("stopped_reason"),
    }

    if output_dir is not None:
        staged = _stage_output_dir(
            output_dir, video_path=video_path, scene_path=scene_file
        )
        detail["staged"] = staged
        video_path = staged.get("video_path", video_path)
        if "scene_path" in staged:
            scene_file = staged["scene_path"]

    ok = True
    error = None
    # if has_audio is False:
    #     ok = False
    #     error = "no_audio_stream"

    return VideoArtifact(
        ok=ok,
        mode="animate",
        video_path=video_path,
        scene_path=scene_file,
        run_dir=run_dir,
        scene_file=scene_file,
        has_audio=has_audio,
        trajectory_path=trajectory_path,
        error=error,
        detail=detail,
    )


async def run_lecture(prompt: str, *, max_validation_attempts: int = 3) -> VideoArtifact:
    """Full IR graph (compile + Docker render) then ffmpeg assemble → lecture_final.mp4."""
    from pydantic_graph import EndMarker

    from graph import AnimationState, animation_graph
    from tools.assemble import assemble_lecture_video

    state = AnimationState(
        user_request=prompt,
        max_validation_attempts=max_validation_attempts,
    )
    try:
        async with animation_graph.iter(state=state) as run:
            async for step in run:
                if isinstance(step, EndMarker):
                    break
                for task in step:
                    print(f"-> {task.node_id}", file=sys.stderr, flush=True)
    except Exception as exc:
        from openai_compatible import format_custom_endpoint_error

        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(state.run_dir) if state.run_dir else None,
            scene_file=_resolve_scene_file(
                state.run_dir, lecture=True
            )
            if state.run_dir
            else None,
            error=format_custom_endpoint_error(str(exc)),
        )

    run_dir = state.run_dir
    if run_dir is None:
        return VideoArtifact(ok=False, mode="lecture", error="no_run_dir")

    scene_file = _resolve_scene_file(run_dir, lecture=True)
    draft = state.lecture_ir
    if draft is None:
        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(run_dir),
            scene_file=scene_file,
            scene_path=scene_file,
            error="missing_lecture_ir",
        )

    render_results_path = Path(run_dir) / "render_results.json"
    if not render_results_path.is_file():
        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(run_dir),
            scene_file=scene_file,
            scene_path=scene_file,
            error="missing_render_results",
        )

    try:
        render_results = json.loads(render_results_path.read_text(encoding="utf-8"))
        video_result = assemble_lecture_video(draft, render_results, Path(run_dir))
    except Exception as exc:
        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(run_dir),
            scene_file=scene_file,
            scene_path=scene_file,
            error=f"assemble_failed: {exc}",
        )

    final_path = video_result.final_video_path
    if not final_path or not Path(final_path).is_file():
        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(run_dir),
            scene_file=scene_file,
            scene_path=scene_file,
            error="assemble_produced_no_final_mp4",
            detail={
                "skipped_scenes": video_result.skipped_scenes,
                "scene_videos": video_result.scene_videos,
            },
        )

    return VideoArtifact(
        ok=True,
        mode="lecture",
        video_path=str(Path(final_path).resolve()),
        scene_path=scene_file,
        run_dir=str(run_dir),
        scene_file=scene_file,
        detail={
            "skipped_scenes": video_result.skipped_scenes,
            "scene_count": len(draft.scenes),
        },
    )


async def run_video(mode: Mode, prompt: str, **kwargs: Any) -> VideoArtifact:
    if mode == "animate":
        return await run_animate(prompt, output_dir=kwargs.get("output_dir"))
    if mode == "lecture":
        return await run_lecture(prompt, **kwargs)
    return VideoArtifact(ok=False, mode="animate", error=f"unknown_mode:{mode}")

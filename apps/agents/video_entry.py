"""Stable entrypoints for UI/Celery: prompt → compiled MP4 path.

Returns a JSON-serializable dict so ``cli.py --json`` and subprocess callers
can parse a single stdout object.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


Mode = Literal["animate", "lecture"]


class VideoArtifact(BaseModel):
    ok: bool
    mode: Mode
    video_path: str | None = None
    run_dir: str | None = None
    error: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


def find_mp4(root: str | Path | None) -> Path | None:
    """Return the largest ``.mp4`` under ``root``, or None."""
    if root is None:
        return None
    base = Path(root)
    if not base.exists():
        return None
    if base.is_file() and base.suffix.lower() == ".mp4":
        return base
    candidates = [p for p in base.rglob("*.mp4") if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_size)


async def run_animate(prompt: str) -> VideoArtifact:
    """Classify → plan → Manim coder/compile; resolve scene MP4."""
    from agent_graph import run_pipeline

    try:
        result = await run_pipeline(prompt)
    except Exception as exc:
        return VideoArtifact(ok=False, mode="animate", error=str(exc))

    run_dir = result.get("run_dir")
    media_hint = result.get("media_hint")
    if not result.get("compile_ok"):
        return VideoArtifact(
            ok=False,
            mode="animate",
            run_dir=run_dir,
            error=result.get("stopped_reason")
            or result.get("message")
            or "compile_failed",
            detail=result if isinstance(result, dict) else {},
        )

    mp4 = find_mp4(media_hint) or find_mp4(run_dir)
    if mp4 is None:
        return VideoArtifact(
            ok=False,
            mode="animate",
            run_dir=run_dir,
            error="compile_ok_but_no_mp4_found",
            detail=result if isinstance(result, dict) else {},
        )

    return VideoArtifact(
        ok=True,
        mode="animate",
        video_path=str(mp4.resolve()),
        run_dir=run_dir,
        detail={
            "scene_name": result.get("scene_name"),
            "stopped_reason": result.get("stopped_reason"),
        },
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
        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(state.run_dir) if state.run_dir else None,
            error=str(exc),
        )

    run_dir = state.run_dir
    if run_dir is None:
        return VideoArtifact(ok=False, mode="lecture", error="no_run_dir")

    draft = state.lecture_ir
    if draft is None:
        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(run_dir),
            error="missing_lecture_ir",
        )

    render_results_path = Path(run_dir) / "render_results.json"
    if not render_results_path.is_file():
        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(run_dir),
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
            error=f"assemble_failed: {exc}",
        )

    final_path = video_result.final_video_path
    if not final_path or not Path(final_path).is_file():
        return VideoArtifact(
            ok=False,
            mode="lecture",
            run_dir=str(run_dir),
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
        run_dir=str(run_dir),
        detail={
            "skipped_scenes": video_result.skipped_scenes,
            "scene_count": len(draft.scenes),
        },
    )


async def run_video(mode: Mode, prompt: str, **kwargs: Any) -> VideoArtifact:
    if mode == "animate":
        return await run_animate(prompt)
    if mode == "lecture":
        return await run_lecture(prompt, **kwargs)
    return VideoArtifact(ok=False, mode="animate", error=f"unknown_mode:{mode}")

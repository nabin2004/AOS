from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pydantic import BaseModel, Field

from ir.manim_ir import LectureIR
from tools.assemble import LectureVideoResult, assemble_lecture_video
from tools.compile import persist_compiled_lecture, persist_lecture_ir
from tools.deps import ToolDeps
from tools.manim_write import write_lecture_py_for_ir
from tools.narrate import BeatNarrationAudio, narrate_lecture_scenes
from tools.render import render_scenes_for_deps, summarize_render_results


# class CodeAgentResult(BaseModel):
#     lecture_py_path: str
#     lecture_ir_path: str
#     narration: list[BeatNarrationAudio]


class LecturePipelineResult(BaseModel):
    lecture_py_path: str
    lecture_ir_path: str
    narration: list[BeatNarrationAudio]
    render_results: dict[str, dict] = Field(default_factory=dict)
    scene_videos: dict[str, str] = Field(default_factory=dict)
    skipped_scenes: list[str] = Field(default_factory=list)
    final_video_path: str | None = None


def persist_pipeline_result(workspace: Path, result: LecturePipelineResult) -> Path:
    """Write full pipeline summary to workspace/pipeline_result.json."""
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / "pipeline_result.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def _apply_audio_durations(
    lecture_ir: LectureIR,
    narration: list[BeatNarrationAudio],
) -> LectureIR:
    """Update beat narration est_seconds from measured wav durations."""
    by_beat_id = {item.beat_id: item.duration_seconds for item in narration}
    if not by_beat_id:
        return lecture_ir

    updated_scenes = []
    for scene in lecture_ir.scenes:
        updated_beats = []
        for beat in scene.beats:
            duration = by_beat_id.get(beat.id)
            if duration is not None and beat.narration is not None:
                updated_beats.append(
                    beat.model_copy(
                        update={
                            "narration": beat.narration.model_copy(
                                update={"est_seconds": duration}
                            )
                        }
                    )
                )
            else:
                updated_beats.append(beat)
        updated_scenes.append(scene.model_copy(update={"beats": updated_beats}))
    return lecture_ir.model_copy(update={"scenes": updated_scenes})


def compile_and_narrate(lecture_ir: LectureIR, deps: ToolDeps) -> CodeAgentResult:
    """Legacy: compile IR to Manim via tools/compile.py and synthesize narration."""
    deps.workspace_dir.mkdir(parents=True, exist_ok=True)

    lecture_ir_path = persist_lecture_ir(deps.workspace_dir, lecture_ir)
    lecture_py_path = ""
    narration: list[BeatNarrationAudio] = []

    try:
        lecture_py_path = str(persist_compiled_lecture(deps.workspace_dir, lecture_ir))
    except Exception as exc:
        print(f"[compile] failed: {exc}")

    try:
        audio_dir = deps.workspace_dir / "audio"
        narration = narrate_lecture_scenes(lecture_ir.scenes, audio_dir)
        if narration:
            lecture_ir = _apply_audio_durations(lecture_ir, narration)
            persist_lecture_ir(deps.workspace_dir, lecture_ir)
            if lecture_py_path:
                persist_compiled_lecture(deps.workspace_dir, lecture_ir)
    except Exception as exc:
        print(f"[narrate] skipped (TTS unavailable): {exc}")

    return CodeAgentResult(
        lecture_py_path=lecture_py_path,
        lecture_ir_path=str(lecture_ir_path),
        narration=narration,
    )


async def write_and_narrate_async(
    lecture_ir: LectureIR, deps: ToolDeps
) -> CodeAgentResult:
    """Write free-form Manim per scene and synthesize narration audio."""
    deps.workspace_dir.mkdir(parents=True, exist_ok=True)
    lecture_ir_path = persist_lecture_ir(deps.workspace_dir, lecture_ir)
    lecture_py_path = ""
    narration: list[BeatNarrationAudio] = []

    try:
        print("[code-writer] generating Manim per scene...")
        lecture_py_path = await write_lecture_py_for_ir(lecture_ir, deps)
        print(f"[code-writer] wrote {lecture_py_path}")
    except Exception as exc:
        print(f"[code-writer] failed: {exc}")

    try:
        audio_dir = deps.workspace_dir / "audio"
        narration = narrate_lecture_scenes(lecture_ir.scenes, audio_dir)
        if narration:
            lecture_ir = _apply_audio_durations(lecture_ir, narration)
            persist_lecture_ir(deps.workspace_dir, lecture_ir)
    except Exception as exc:
        print(f"[narrate] skipped (TTS unavailable): {exc}")

    return CodeAgentResult(
        lecture_py_path=lecture_py_path,
        lecture_ir_path=str(lecture_ir_path),
        narration=narration,
    )


def write_and_narrate(lecture_ir: LectureIR, deps: ToolDeps) -> CodeAgentResult:
    """Sync wrapper for CLI callers only (not safe inside an async event loop)."""
    return asyncio.run(write_and_narrate_async(lecture_ir, deps))


async def run_full_pipeline_async(
    lecture_ir: LectureIR, deps: ToolDeps
) -> LecturePipelineResult:
    """Write Manim, narrate, render, mux, and concatenate into lecture_final.mp4."""
    deps.workspace_dir.mkdir(parents=True, exist_ok=True)

    code = await write_and_narrate_async(lecture_ir, deps)
    lecture_ir = LectureIR.model_validate_json(
        Path(code.lecture_ir_path).read_text(encoding="utf-8")
    )

    render_results: dict[str, dict] = {}
    video_result = LectureVideoResult()

    if code.lecture_py_path and Path(code.lecture_py_path).exists():
        print("[render] starting Docker Manim renders (isolated containers)...")
        render_deps = ToolDeps(
            workspace_dir=deps.workspace_dir,
            docker_image=deps.docker_image,
            persistent_container=False,
        )
        render_results = render_scenes_for_deps(
            render_deps,
            scene_file="lecture.py",
            scene_classes=[s.class_name for s in lecture_ir.scenes],
            render_config=lecture_ir.render,
        )
        render_results_path = deps.workspace_dir / "render_results.json"
        render_results_path.write_text(
            json.dumps(render_results, indent=2, default=str),
            encoding="utf-8",
        )
        summary = summarize_render_results(render_results)
        print(
            f"[render] {summary['succeeded']}/{summary['attempted']} succeeded, "
            f"{summary['failed']} failed — {render_results_path}"
        )
        for scene_class, snippet in summary["failures"]:
            safe = snippet.encode("ascii", errors="replace").decode("ascii")
            print(f"[render]   {scene_class}: {safe}")

        try:
            video_result = assemble_lecture_video(
                lecture_ir, render_results, deps.workspace_dir
            )
        except Exception as exc:
            print(f"[assemble] skipped: {exc}")
    else:
        print("[render] skipped: lecture.py missing")

    result = LecturePipelineResult(
        lecture_py_path=code.lecture_py_path,
        lecture_ir_path=code.lecture_ir_path,
        narration=code.narration,
        render_results=render_results,
        scene_videos=video_result.scene_videos,
        skipped_scenes=video_result.skipped_scenes,
        final_video_path=video_result.final_video_path,
    )
    summary_path = persist_pipeline_result(deps.workspace_dir, result)
    print(f"[pipeline] results: {summary_path}")
    return result


def run_full_pipeline(lecture_ir: LectureIR, deps: ToolDeps) -> LecturePipelineResult:
    """Sync entry point for CLI tools (assemble_runner). Do not call from async graph nodes."""
    return asyncio.run(run_full_pipeline_async(lecture_ir, deps))

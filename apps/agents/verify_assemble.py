"""Smoke-test assemble/pipeline helpers on an existing workspace."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from ir.manim_ir import LectureIR
from tools.assemble import (
    assemble_lecture_video,
    build_scene_audio_track,
    concat_scene_videos,
    mux_scene_video,
    probe_duration_seconds,
)

DEFAULT_WORKSPACE = Path("runs") / "final_final_graph"


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _make_test_video(path: Path, seconds: float = 1.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=320x240:d={seconds}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"failed to create test video: {proc.stderr[-300:]}")
    return path


def main(workspace: Path = DEFAULT_WORKSPACE) -> int:
    ir_path = workspace / "lecture_ir.json"
    if not ir_path.exists():
        print(f"SKIP: missing {ir_path}")
        return 1

    lecture_ir = LectureIR.model_validate_json(ir_path.read_text(encoding="utf-8"))
    audio_dir = workspace / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    tracks_built = 0
    for scene in lecture_ir.scenes:
        track = build_scene_audio_track(scene, audio_dir)
        if track and track.exists():
            tracks_built += 1
            print(f"audio track: {track.name}")
    print(f"built {tracks_built}/{len(lecture_ir.scenes)} scene audio track(s)")

    failed_render = {scene.class_name: {"success": False} for scene in lecture_ir.scenes}
    skip_result = assemble_lecture_video(lecture_ir, failed_render, workspace)
    assert skip_result.final_video_path is None
    assert len(skip_result.skipped_scenes) == len(lecture_ir.scenes)
    print("skipped all scenes when render failed (no crash)")

    if not _ffmpeg_available():
        print("ffmpeg not on PATH — audio/skip checks passed; install ffmpeg for mux/concat")
        return 0

    videos_dir = workspace / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    test_video = videos_dir / "_verify_scene.mp4"
    _make_test_video(test_video, seconds=0.5)
    first_scene = lecture_ir.scenes[0]
    track = audio_dir / f"{first_scene.class_name}_track.wav"
    if not track.exists():
        track = build_scene_audio_track(first_scene, audio_dir)
    if track is None:
        print("SKIP mux: no audio track for first scene")
        return 0

    muxed = videos_dir / "_verify_muxed.mp4"
    mux_scene_video(test_video, track, muxed)
    assert muxed.exists()
    print(f"mux ok: {muxed.name} ({probe_duration_seconds(muxed):.2f}s)")

    final = workspace / "_verify_concat.mp4"
    concat_scene_videos([muxed, muxed], final)
    assert final.exists()
    print(f"concat ok: {final.name} ({probe_duration_seconds(final):.2f}s)")
    return 0


if __name__ == "__main__":
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_WORKSPACE
    raise SystemExit(main(ws))

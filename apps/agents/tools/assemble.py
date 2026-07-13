from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import scipy.io.wavfile
from pydantic import BaseModel, Field

from ir.manim_ir import LectureIR, Scene
from tools.narrate import wav_duration_seconds


class LectureVideoResult(BaseModel):
    scene_videos: dict[str, str] = Field(default_factory=dict)
    scene_audio_tracks: dict[str, str] = Field(default_factory=dict)
    skipped_scenes: list[str] = Field(default_factory=list)
    final_video_path: str | None = None


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg to mux narration and assemble the final video."
        )
    return path


def _require_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if not path:
        raise RuntimeError(
            "ffprobe not found on PATH. Install ffmpeg (includes ffprobe) for video duration probing."
        )
    return path


def probe_duration_seconds(media_path: Path) -> float:
    """Return media duration in seconds via ffprobe."""
    _require_ffprobe()
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return 0.0
    return float(proc.stdout.strip())


def scene_audio_path(class_name: str, beat_index: int, audio_dir: Path) -> Path:
    return audio_dir / f"{class_name}_{beat_index:02d}.wav"


def _silence(rate: int, seconds: float, channels: int = 1) -> np.ndarray:
    if seconds <= 0:
        return np.array([], dtype=np.int16)
    n_samples = int(round(rate * seconds))
    if channels == 1:
        return np.zeros(n_samples, dtype=np.int16)
    return np.zeros((n_samples, channels), dtype=np.int16)


def _read_wav(path: Path) -> tuple[int, np.ndarray]:
    rate, data = scipy.io.wavfile.read(path)
    if data.dtype != np.int16:
        data = data.astype(np.int16)
    return rate, data


def _concat_wav_segments(segments: list[np.ndarray], rate: int, out_path: Path) -> Path:
    if not segments:
        return out_path
    combined = np.concatenate(segments)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scipy.io.wavfile.write(out_path, rate, combined)
    return out_path


def build_scene_audio_track(scene: Scene, audio_dir: Path) -> Path | None:
    """Build IR-timed narration track: silence during animation, wav during hold."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_path = audio_dir / f"{scene.class_name}_track.wav"
    segments: list[np.ndarray] = []
    rate: int | None = None

    for beat_index, beat in enumerate(scene.beats):
        if beat.animation_segment:
            anim_sec = sum(op.run_time for op in beat.animation_segment)
        else:
            anim_sec = beat.animation_seconds
        wav_path = scene_audio_path(scene.class_name, beat_index, audio_dir)

        if rate is None and wav_path.exists():
            rate, _ = _read_wav(wav_path)
        elif rate is None:
            rate = 24000

        segments.append(_silence(rate, anim_sec))

        if wav_path.exists():
            _, data = _read_wav(wav_path)
            segments.append(data)
            narr_duration = wav_duration_seconds(wav_path)
            trailing = max(0.0, beat.hold_seconds - narr_duration)
            if trailing > 0:
                channels = 1 if data.ndim == 1 else data.shape[1]
                segments.append(_silence(rate, trailing, channels))
        elif beat.hold_seconds > 0:
            segments.append(_silence(rate, beat.hold_seconds))

    if not segments or rate is None:
        return None

    return _concat_wav_segments(segments, rate, out_path)


def _pad_audio_track_to_duration(audio_path: Path, target_seconds: float) -> Path:
    """Append silence so the audio track is at least target_seconds long."""
    if target_seconds <= 0:
        return audio_path
    current = probe_duration_seconds(audio_path)
    pad_seconds = target_seconds - current
    if pad_seconds <= 0.05:
        return audio_path

    rate, data = _read_wav(audio_path)
    channels = 1 if data.ndim == 1 else data.shape[1]
    padded = np.concatenate([data, _silence(rate, pad_seconds, channels)])
    scipy.io.wavfile.write(audio_path, rate, padded)
    return audio_path


def mux_scene_video(video_path: Path, audio_path: Path, out_path: Path) -> Path:
    """Mux rendered Manim video with the scene narration track."""
    _require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    video_duration = probe_duration_seconds(video_path)
    if video_duration > 0:
        _pad_audio_track_to_duration(audio_path, video_duration)

    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg mux failed for {out_path.name}: {proc.stderr[-500:]}")
    return out_path


def concat_scene_videos(video_paths: list[Path], out_path: Path) -> Path:
    """Concatenate scene videos in order into one lecture file."""
    _require_ffmpeg()
    if not video_paths:
        raise ValueError("no scene videos to concatenate")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    list_file = out_path.with_suffix(".concat.txt")
    lines = []
    for path in video_paths:
        escaped = str(path.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {proc.stderr[-500:]}")
    return out_path


def assemble_lecture_video(
    lecture_ir: LectureIR,
    render_results: dict[str, dict],
    workspace: Path,
) -> LectureVideoResult:
    """Mux per-scene renders with IR-timed audio and concatenate into lecture_final.mp4."""
    workspace.mkdir(parents=True, exist_ok=True)
    audio_dir = workspace / "audio"
    videos_dir = workspace / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    result = LectureVideoResult()
    muxed_paths: list[Path] = []

    for scene in lecture_ir.scenes:
        class_name = scene.class_name
        render = render_results.get(class_name, {})
        if not render.get("success") or not render.get("output_path"):
            result.skipped_scenes.append(class_name)
            print(f"[assemble] skipped {class_name}: render failed or missing output")
            continue

        video_src = Path(render["output_path"])
        if not video_src.exists():
            result.skipped_scenes.append(class_name)
            print(f"[assemble] skipped {class_name}: video not found at {video_src}")
            continue

        stable_video = videos_dir / f"{class_name}.mp4"
        if video_src.resolve() != stable_video.resolve():
            shutil.copy2(video_src, stable_video)

        audio_track = build_scene_audio_track(scene, audio_dir)
        if audio_track is None or not audio_track.exists():
            result.skipped_scenes.append(class_name)
            print(f"[assemble] skipped {class_name}: no narration audio track")
            continue

        result.scene_audio_tracks[class_name] = str(audio_track)
        muxed = videos_dir / f"{class_name}_with_audio.mp4"
        try:
            mux_scene_video(stable_video, audio_track, muxed)
        except Exception as exc:
            result.skipped_scenes.append(class_name)
            print(f"[assemble] skipped {class_name}: mux failed ({exc})")
            continue

        result.scene_videos[class_name] = str(muxed)
        muxed_paths.append(muxed)

    if muxed_paths:
        final_path = workspace / "lecture_final.mp4"
        try:
            concat_scene_videos(muxed_paths, final_path)
            result.final_video_path = str(final_path)
        except Exception as exc:
            print(f"[assemble] concat failed: {exc}")

    summary_path = workspace / "assemble_result.json"
    summary_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result

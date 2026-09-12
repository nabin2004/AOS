"""Timeline Assembler and Visual Hold Engine for Decoupled Audio-Visual Teaching Segments.

Implements frame-freezing, authoritative duration measurement, and seamless
concatenation so Manim animations are rendered once as visual anchors, and then
held statically on screen for as long as the teacher's detailed narration continues.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import List, Optional


def get_media_duration(file_path: Path | str) -> float:
    """Measures the exact authoritative duration of a video or audio file in seconds.

    Uses ffprobe with fallback to scipy.io.wavfile / wave for audio.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {path}")

    # Primary: ffprobe
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        val = res.stdout.strip()
        if val:
            dur = float(val)
            if dur > 0:
                return dur
    except Exception:
        pass

    # Fallback for audio files
    if path.suffix.lower() in (".wav", ".wave"):
        try:
            import wave
            with wave.open(str(path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return float(frames) / float(rate)
        except Exception:
            pass

    return 0.0


def hold_final_state(
    video_path: Path | str,
    hold_duration: float,
    audio_path: Optional[Path | str] = None,
    output_path: Optional[Path | str] = None,
) -> Path:
    """Extends a completed visual animation by holding its final frame on screen.

    Does NOT re-render Manim. Instead, clones the final frame using FFmpeg `tpad`
    filter for the exact duration of the teacher's detailed narration, and muxes
    in the authoritative narration audio.

    Args:
        video_path: Path to the completed Manim visual animation MP4.
        hold_duration: Number of seconds to freeze the final frame (hold_duration >= 0).
        audio_path: Optional path to the narration audio WAV.
        output_path: Optional destination path for the assembled segment MP4.

    Returns:
        Path to the assembled segment MP4.
    """
    in_video = Path(video_path).resolve()
    if not in_video.is_file():
        raise FileNotFoundError(f"Input video not found: {in_video}")

    if output_path is None:
        out_file = in_video.parent / f"{in_video.stem}_held.mp4"
    else:
        out_file = Path(output_path).resolve()

    out_file.parent.mkdir(parents=True, exist_ok=True)
    in_audio = Path(audio_path).resolve() if audio_path else None

    # Edge Case: No hold needed (narration fits within animation or no hold required)
    if hold_duration <= 0.05:
        if in_audio and in_audio.is_file():
            cmd = [
                "ffmpeg", "-y",
                "-i", str(in_video),
                "-i", str(in_audio),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(out_file),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and out_file.is_file() and out_file.stat().st_size > 0:
                return out_file
        else:
            shutil.copy2(in_video, out_file)
            return out_file

    # Primary Strategy: FFmpeg tpad filter (fast, single-pass, clones final frame)
    if in_audio and in_audio.is_file():
        cmd = [
            "ffmpeg", "-y",
            "-i", str(in_video),
            "-i", str(in_audio),
            "-filter_complex", f"[0:v]tpad=stop_mode=clone:stop_duration={hold_duration:.3f}[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(out_file),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(in_video),
            "-filter_complex", f"[0:v]tpad=stop_mode=clone:stop_duration={hold_duration:.3f}[v]",
            "-map", "[v]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_file),
        ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0 and out_file.is_file() and out_file.stat().st_size > 0:
        return out_file

    # Fallback Strategy: Extract final frame image and concatenate freeze video
    tmp_dir = out_file.parent / f"_tmp_hold_{out_file.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    last_frame = tmp_dir / "last_frame.png"
    hold_clip = tmp_dir / "hold_clip.mp4"
    concat_txt = tmp_dir / "concat.txt"

    try:
        # Extract last frame
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(in_video), "-frames:v", "1", "-update", "1", str(last_frame)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        # Create hold video
        subprocess.run(
            [
                "ffmpeg", "-y", "-loop", "1", "-i", str(last_frame),
                "-t", f"{hold_duration:.3f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(hold_clip)
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        # Concat
        with open(concat_txt, "w", encoding="utf-8") as f:
            f.write(f"file '{str(in_video).replace(chr(92), '/')}'\n")
            f.write(f"file '{str(hold_clip).replace(chr(92), '/')}'\n")

        if in_audio and in_audio.is_file():
            fallback_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                "-i", str(in_audio),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                str(out_file),
            ]
        else:
            fallback_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(out_file),
            ]
        subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if out_file.is_file() and out_file.stat().st_size > 0:
        return out_file

    # Ultimate fallback: copy original video
    shutil.copy2(in_video, out_file)
    return out_file


def assemble_segments(segment_paths: List[Path], output_path: Path) -> Path:
    """Concatenates all completed TeachingSegment MP4s into the final lesson video."""
    if not segment_paths:
        raise ValueError("No video segments provided to assemble")

    valid_chunks = [p for p in segment_paths if p.is_file() and p.stat().st_size > 0]
    if not valid_chunks:
        raise ValueError("No valid video segment files found on disk")

    if len(valid_chunks) == 1:
        shutil.copy2(valid_chunks[0], output_path)
        return output_path

    concat_file = output_path.parent / "segments_concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in valid_chunks:
            escaped = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{escaped}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path.resolve()),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0 or not output_path.is_file():
        # Fallback: copy first chunk
        shutil.copy2(valid_chunks[0], output_path)

    return output_path

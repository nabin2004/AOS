"""Video output validator for Manim-rendered videos.

Verifies that rendered MP4s are non-empty, uncorrupted, and have valid dimensions and duration.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any

from reliability_config import MIN_VIDEO_SIZE_BYTES


@dataclass
class VideoValidationResult:
    ok: bool
    video_path: str
    file_size_bytes: int
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    codec: str | None = None
    has_audio: bool | None = None
    error: str | None = None
    detail: dict[str, Any] | None = None


def _probe_with_ffprobe(path: Path) -> dict[str, Any] | None:
    """Run ffprobe to extract stream and format metadata."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if proc.returncode != 0:
            return None
        return json.loads(proc.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def _inspect_mp4_atoms_fallback(path: Path) -> bool:
    """Quick binary sanity check for valid MP4 atoms if ffprobe is absent."""
    try:
        data = path.read_bytes()[:4096]
        # Standard MP4 container starts with ftyp box
        return b"ftyp" in data or b"moov" in data
    except Exception:
        return False


def validate_video_file(
    video_path: str | Path | None,
    *,
    min_bytes: int = MIN_VIDEO_SIZE_BYTES,
) -> VideoValidationResult:
    """Validate that the given video file exists, is non-empty, and playable."""
    if not video_path:
        return VideoValidationResult(
            ok=False,
            video_path="",
            file_size_bytes=0,
            error="Video file path is None or empty",
        )

    p = Path(video_path)
    if not p.exists():
        return VideoValidationResult(
            ok=False,
            video_path=str(p),
            file_size_bytes=0,
            error=f"Video file does not exist: {p.name}",
        )

    if not p.is_file():
        return VideoValidationResult(
            ok=False,
            video_path=str(p),
            file_size_bytes=0,
            error=f"Video path is not a file: {p.name}",
        )

    size = p.stat().st_size
    if size < min_bytes:
        return VideoValidationResult(
            ok=False,
            video_path=str(p),
            file_size_bytes=size,
            error=f"Video file is too small ({size} bytes < {min_bytes} threshold), likely aborted or corrupted",
        )

    # Try ffprobe probe
    info = _probe_with_ffprobe(p)
    if info is not None:
        streams = info.get("streams", [])
        fmt = info.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not video_stream:
            return VideoValidationResult(
                ok=False,
                video_path=str(p),
                file_size_bytes=size,
                error="Rendered MP4 contains no video stream",
                detail=info,
            )

        # Parse duration
        dur_str = video_stream.get("duration") or fmt.get("duration")
        duration = None
        if dur_str is not None:
            try:
                duration = float(dur_str)
            except (ValueError, TypeError):
                duration = None

        if duration is not None and duration <= 0.05:
            return VideoValidationResult(
                ok=False,
                video_path=str(p),
                file_size_bytes=size,
                duration_seconds=duration,
                error=f"Rendered video duration is effectively 0 ({duration:.2f}s)",
                detail=info,
            )

        width = video_stream.get("width")
        height = video_stream.get("height")
        codec = video_stream.get("codec_name")

        return VideoValidationResult(
            ok=True,
            video_path=str(p),
            file_size_bytes=size,
            duration_seconds=duration,
            width=width,
            height=height,
            codec=codec,
            has_audio=audio_stream is not None,
            detail={"format": fmt.get("format_name")},
        )

    # Fallback if ffprobe is not installed on system
    if not _inspect_mp4_atoms_fallback(p):
        return VideoValidationResult(
            ok=False,
            video_path=str(p),
            file_size_bytes=size,
            error="File does not appear to be a valid MP4 container (missing ftyp/moov box)",
        )

    return VideoValidationResult(
        ok=True,
        video_path=str(p),
        file_size_bytes=size,
        detail={"probe": "atom_fallback"},
    )

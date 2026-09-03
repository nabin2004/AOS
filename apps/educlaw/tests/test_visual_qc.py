"""Unit tests for Visual QC and Keyframe Inspection."""

import pytest
from pathlib import Path

from educlaw.animateworkflow.contracts import FrameInspection, VisualQCReport
from educlaw.animateworkflow.visual_qc import (
    extract_keyframes,
    get_vision_model,
    inspect_keyframe_mock,
    inspect_video_frames,
)


def test_get_vision_model_default(monkeypatch):
    monkeypatch.delenv("EDUCLAW_VISION_MODEL", raising=False)
    model = get_vision_model()
    assert "gpt-4o-mini" in model


def test_get_vision_model_custom(monkeypatch):
    monkeypatch.setenv("EDUCLAW_VISION_MODEL", "openrouter:anthropic/claude-3.5-sonnet")
    model = get_vision_model()
    assert "claude-3.5-sonnet" in model


def test_extract_keyframes_nonexistent(tmp_path: Path):
    frames = extract_keyframes(tmp_path / "nonexistent.mp4", tmp_path / "frames")
    assert frames == []


def test_inspect_keyframe_mock(tmp_path: Path):
    dummy_frame = tmp_path / "frame_001.png"
    dummy_frame.write_bytes(b"PNG fake")
    insp = inspect_keyframe_mock(dummy_frame, 2.0)
    assert insp.timestamp_sec == 2.0
    assert not insp.has_overlaps
    assert not insp.has_clipping


@pytest.mark.asyncio
async def test_inspect_video_frames_mock(tmp_path: Path, monkeypatch):
    video_path = tmp_path / "dummy.mp4"
    video_path.write_bytes(b"fake mp4")

    # Mock extract_keyframes to return dummy files
    f1 = tmp_path / "frame_001.png"
    f2 = tmp_path / "frame_002.png"
    f1.write_bytes(b"png1")
    f2.write_bytes(b"png2")

    monkeypatch.setattr(
        "educlaw.animateworkflow.visual_qc.extract_keyframes",
        lambda *args, **kwargs: [f1, f2],
    )

    report = await inspect_video_frames(video_path, tmp_path / "frames", mock=True)
    assert report.passed is True
    assert len(report.inspected_frames) == 2
    assert "Passed" in report.summary

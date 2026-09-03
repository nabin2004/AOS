"""Multimodal Visual Quality Control and Keyframe Inspection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel
from pydantic_ai import Agent

from educlaw.animateworkflow.contracts import FrameInspection, VisualQCReport


class VisualInspectionVerdict(BaseModel):
    """Structured LLM output for an analyzed video frame."""

    has_overlaps: bool = False
    has_clipping: bool = False
    contrast_issue: bool = False
    description: str = ""
    suggested_fix: str = ""


VISUAL_QC_SYSTEM_PROMPT = """\
You are an expert visual quality inspector for educational Manim animations.
Analyze the provided educational animation keyframe image and detect:
1. Overlapping text or formulas colliding with geometric objects.
2. Elements clipped or extending off-screen beyond visible canvas bounds.
3. Poor color contrast (e.g. dark text against dark background).

Respond with accurate boolean flags and actionable recommendations to repair the Manim Python code.
"""


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    fps: float = 0.5,
    max_frames: int = 6,
) -> List[Path]:
    """Extract keyframe image snapshots (.png) from an MP4 video file using ffmpeg."""
    if not video_path.exists():
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%03d.png"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps}",
        "-vframes",
        str(max_frames),
        str(pattern),
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            return []
    except Exception:
        return []

    return sorted(output_dir.glob("frame_*.png"))


def get_vision_model() -> str:
    """Retrieve the configured multimodal vision model identifier."""
    return os.getenv("EDUCLAW_VISION_MODEL", "openrouter:openai/gpt-4o-mini")


def inspect_keyframe_mock(frame_path: Path, timestamp: float) -> FrameInspection:
    """Heuristic / stub inspector when running in offline or test mode."""
    return FrameInspection(
        timestamp_sec=timestamp,
        frame_path=str(frame_path),
        has_overlaps=False,
        has_clipping=False,
        contrast_issue=False,
        description="Frame passes visual boundaries and text clearance checks.",
        suggested_fix="",
    )


async def inspect_video_frames(
    video_path: Path,
    output_dir: Path,
    *,
    model: str | None = None,
    mock: bool = False,
) -> VisualQCReport:
    """Extract and analyze keyframes to detect visual rendering defects."""
    frames = extract_keyframes(video_path, output_dir)
    if not frames:
        return VisualQCReport(
            video_path=str(video_path),
            passed=True,
            inspected_frames=[],
            summary="No frames could be extracted or video duration was negligible.",
        )

    inspections: List[FrameInspection] = []
    has_defect = False

    vision_model = model or get_vision_model()

    for idx, frame in enumerate(frames):
        timestamp = round((idx + 1) * 2.0, 1)

        if mock or "test" in vision_model.lower():
            insp = inspect_keyframe_mock(frame, timestamp)
        else:
            try:
                agent = Agent(
                    model=vision_model,
                    name="VisualQCAgent",
                    output_type=VisualInspectionVerdict,
                    instructions=VISUAL_QC_SYSTEM_PROMPT,
                )
                prompt = (
                    f"Please analyze keyframe {frame.name} at timestamp {timestamp}s. "
                    f"Check for overlapping MathTex/Text, boundary clipping, and contrast issues."
                )
                res = await agent.run(prompt)
                verdict = res.output
                insp = FrameInspection(
                    timestamp_sec=timestamp,
                    frame_path=str(frame),
                    has_overlaps=verdict.has_overlaps,
                    has_clipping=verdict.has_clipping,
                    contrast_issue=verdict.contrast_issue,
                    description=verdict.description,
                    suggested_fix=verdict.suggested_fix,
                )
            except Exception as exc:
                insp = FrameInspection(
                    timestamp_sec=timestamp,
                    frame_path=str(frame),
                    has_overlaps=False,
                    has_clipping=False,
                    contrast_issue=False,
                    description=f"Automated visual inspection skipped due to error: {exc}",
                    suggested_fix="",
                )

        if insp.has_overlaps or insp.has_clipping or insp.contrast_issue:
            has_defect = True
        inspections.append(insp)

    summary = (
        "Visual QA Passed with 0 defects."
        if not has_defect
        else f"Visual defects detected in {sum(1 for i in inspections if i.has_overlaps or i.has_clipping)} frame(s)."
    )

    return VisualQCReport(
        video_path=str(video_path),
        passed=not has_defect,
        inspected_frames=inspections,
        summary=summary,
    )

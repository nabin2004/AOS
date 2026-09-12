"""Tests for Decoupled Audio-Visual TeachingSegment Architecture."""

from pathlib import Path
import pytest

from ir import SemanticEvent, TeachingSegment, VisualAnchor
from tools.timeline_assembler import (
    assemble_segments,
    get_media_duration,
    hold_final_state,
)


def test_teaching_segment_model():
    """Verify TeachingSegment correctly handles decoupled visual and narration durations."""
    anchor = VisualAnchor(
        type="formula",
        title="Euler's Formula",
        latex=r"e^{i\theta} = \cos(\theta) + i\sin(\theta)",
        visible_elements=["e", "i", "theta", "cos", "sin"],
        visual_purpose="Bridge exponential growth and circular trigonometry.",
    )
    segment = TeachingSegment(
        slide_num=1,
        concept="Euler's Formula",
        learning_objective="Understand complex rotation",
        visual_anchor=anchor,
        manim_code="self.play(Write(MathTex(r'e^{i\\theta}')))",
        narration="Here is a comprehensive 75-second explanation of Euler's formula...",
        visual_duration=8.5,
        narration_duration=74.2,
    )

    # Invariant: visual_duration != narration_duration
    assert segment.visual_duration != segment.narration_duration
    assert segment.visual_duration == 8.5
    assert segment.narration_duration == 74.2

    # Invariant: Total duration governed authoritatively by narration
    assert segment.total_duration == 74.2

    # Invariant: Hold duration is exact difference
    assert pytest.approx(segment.hold_duration, 0.01) == 65.7


def test_hold_final_state_decoupling(tmp_path: Path):
    """Verify hold_final_state extends visual video by freezing final frame without re-rendering."""
    # Locate an existing rendered video from previous runs or create a test clip
    sample_videos = list(Path("apps/agents/workspace/producer_consumer_runs").rglob("slide_1.mp4"))
    if not sample_videos:
        pytest.skip("No sample video found in workspace for hold_final_state test")

    in_video = sample_videos[0]
    initial_duration = get_media_duration(in_video)
    assert initial_duration > 0

    hold_seconds = 4.5
    out_video = tmp_path / "extended_segment.mp4"

    res = hold_final_state(
        video_path=in_video,
        hold_duration=hold_seconds,
        output_path=out_video,
    )

    assert res.is_file()
    assert res.stat().st_size > 0

    new_duration = get_media_duration(res)
    # The new duration should equal initial_duration + hold_seconds
    expected_duration = initial_duration + hold_seconds
    assert pytest.approx(new_duration, abs=0.5) == expected_duration

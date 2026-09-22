from pathlib import Path

from video_validator import validate_video_file


def test_missing_video_is_rejected() -> None:
    result = validate_video_file(Path("does-not-exist.mp4"))

    assert not result.ok
    assert "does not exist" in (result.error or "")

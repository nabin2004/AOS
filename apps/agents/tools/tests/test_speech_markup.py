"""Unit tests for Pocket TTS bookmark markup parsing / boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

# Prefer importing the module file directly so this file can run without the
# full agents package graph (tools/__init__.py pulls compile → apps.agents).
_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from speech_markup import (  # noqa: E402
    AUDIO_OFFSET_RESOLUTION,
    bookmark_time,
    build_segment_word_boundaries,
    parse_bookmarks,
)


def test_parse_bookmarks_focus_offset() -> None:
    text = "Before we start our <bookmark mark='FOCUS'/>lecture One."
    parsed = parse_bookmarks(text)

    assert parsed.clean_text == "Before we start our lecture One."
    assert parsed.has_bookmarks
    assert parsed.segments == ["Before we start our ", "lecture One."]
    assert parsed.bookmarks == [
        {"mark": "FOCUS", "text_offset": len("Before we start our ")}
    ]
    assert parsed.bookmarks[0]["text_offset"] == 20


def test_parse_bookmarks_double_quotes_and_multiple() -> None:
    text = (
        'We have <bookmark mark="A"/>concept A, '
        "<bookmark mark='B'/>concept B."
    )
    parsed = parse_bookmarks(text)

    assert parsed.clean_text == "We have concept A, concept B."
    assert [b["mark"] for b in parsed.bookmarks] == ["A", "B"]
    assert parsed.bookmarks[0]["text_offset"] == len("We have ")
    assert parsed.bookmarks[1]["text_offset"] == len("We have concept A, ")
    assert parsed.segments == ["We have ", "concept A, ", "concept B."]


def test_parse_bookmarks_none() -> None:
    parsed = parse_bookmarks("Hello everyone.")
    assert not parsed.has_bookmarks
    assert parsed.clean_text == "Hello everyone."
    assert parsed.segments == ["Hello everyone."]
    assert parsed.bookmarks == []


def test_parse_bookmark_at_start() -> None:
    parsed = parse_bookmarks("<bookmark mark='START'/>Hello.")
    assert parsed.segments == ["", "Hello."]
    assert parsed.bookmarks == [{"mark": "START", "text_offset": 0}]
    assert parsed.clean_text == "Hello."


def test_segment_word_boundaries_map_focus_to_first_segment_end() -> None:
    segments = ["Before we start our ", "lecture One."]
    durations = [1.42, 0.68]
    boundaries = build_segment_word_boundaries(segments, durations)

    assert boundaries[0]["text_offset"] == 0
    assert boundaries[0]["audio_offset"] == 0
    assert boundaries[1]["text_offset"] == 20
    assert boundaries[1]["audio_offset"] == int(1.42 * AUDIO_OFFSET_RESOLUTION)
    assert boundaries[2]["text_offset"] == 20 + len("lecture One.")
    assert boundaries[2]["audio_offset"] == int(
        (1.42 + 0.68) * AUDIO_OFFSET_RESOLUTION
    )

    bookmarks = [{"mark": "FOCUS", "text_offset": 20}]
    assert bookmark_time(bookmarks, boundaries, "FOCUS") == 1.42


def test_empty_segment_contributes_zero_duration() -> None:
    segments = ["", "Hello."]
    durations = [0.0, 0.5]
    boundaries = build_segment_word_boundaries(segments, durations)
    bookmarks = [{"mark": "START", "text_offset": 0}]
    assert bookmark_time(bookmarks, boundaries, "START") == 0.0


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"ok {fn.__name__}")
    print(f"ran {len(tests)} tests")

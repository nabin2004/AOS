"""Parse Manim Voiceover bookmark markup for AOS Pocket TTS alignment.

Manim expects ``<bookmark mark='NAME'/>`` tags in voiceover text and maps them
to audio times via ``word_boundaries``. Pocket TTS has no native timestamps, so
we split synthesis at bookmark edges and emit boundaries at measured segment
ends (no Whisper).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

# Same resolution Manim Voiceover uses in tracker.TimeInterpolator.
AUDIO_OFFSET_RESOLUTION = 10_000_000

# Matches Manim's bookmark tag (see manim_voiceover.helper / tracker).
_BOOKMARK_SPLIT_RE = re.compile(r"(<bookmark\s*mark\s*=['\"]\w*['\"]\s*/>)")
_BOOKMARK_MARK_RE = re.compile(r"<bookmark\s*mark\s*=['\"](\w*)['\"]\s*/>")


class BookmarkMark(TypedDict):
    mark: str
    text_offset: int


class WordBoundary(TypedDict):
    audio_offset: int
    text_offset: int
    word_length: int
    text: str
    boundary_type: str


@dataclass(frozen=True)
class ParsedSpeechMarkup:
    """Result of parsing Manim bookmark tags out of voiceover text."""

    clean_text: str
    segments: list[str]
    bookmarks: list[BookmarkMark]

    @property
    def has_bookmarks(self) -> bool:
        return bool(self.bookmarks)


def parse_bookmarks(text: str) -> ParsedSpeechMarkup:
    """Split voiceover text on Manim ``<bookmark mark='…'/>`` tags.

    Returns clean spoken text, ordered text segments between marks, and each
    mark's character offset in the clean text.
    """
    parts = _BOOKMARK_SPLIT_RE.split(text)
    segments: list[str] = []
    bookmarks: list[BookmarkMark] = []
    clean_parts: list[str] = []
    text_offset = 0
    pending_segment = ""

    for part in parts:
        if not part:
            continue
        matched = _BOOKMARK_MARK_RE.fullmatch(part)
        if matched:
            segments.append(pending_segment)
            clean_parts.append(pending_segment)
            text_offset += len(pending_segment)
            pending_segment = ""
            bookmarks.append({"mark": matched.group(1), "text_offset": text_offset})
        else:
            pending_segment += part

    segments.append(pending_segment)
    clean_parts.append(pending_segment)

    return ParsedSpeechMarkup(
        clean_text="".join(clean_parts),
        segments=segments,
        bookmarks=bookmarks,
    )


def build_segment_word_boundaries(
    segments: list[str],
    segment_durations: list[float],
) -> list[WordBoundary]:
    """Build Manim ``word_boundaries`` at segment edges from measured durations.

    Bookmark char offsets land on segment boundaries, so interpolation yields
    the end time of the preceding segment (empty segments contribute 0s).
    """
    if len(segments) != len(segment_durations):
        raise ValueError(
            f"segments ({len(segments)}) and durations ({len(segment_durations)}) "
            "must have the same length"
        )

    boundaries: list[WordBoundary] = [
        {
            "audio_offset": 0,
            "text_offset": 0,
            "word_length": 0,
            "text": "",
            "boundary_type": "Word",
        }
    ]

    text_offset = 0
    audio_time = 0.0
    for segment, duration in zip(segments, segment_durations, strict=True):
        text_offset += len(segment)
        audio_time += max(0.0, float(duration))
        boundaries.append(
            {
                "audio_offset": int(audio_time * AUDIO_OFFSET_RESOLUTION),
                "text_offset": text_offset,
                "word_length": len(segment),
                "text": segment,
                "boundary_type": "Word",
            }
        )

    return boundaries


def bookmark_time(
    bookmarks: list[BookmarkMark],
    word_boundaries: list[WordBoundary],
    mark: str,
) -> float:
    """Return audio time (seconds) for ``mark`` using segment-edge boundaries.

    Used by unit tests; Manim's tracker performs the same interpolation at runtime.
    """
    target = next((b for b in bookmarks if b["mark"] == mark), None)
    if target is None:
        raise KeyError(f"No bookmark mark={mark!r}")

    offset = target["text_offset"]
    for wb in word_boundaries:
        if wb["text_offset"] == offset:
            return wb["audio_offset"] / AUDIO_OFFSET_RESOLUTION

    # Exact edge miss: linear interpolate between surrounding boundaries.
    prev = word_boundaries[0]
    for wb in word_boundaries[1:]:
        if prev["text_offset"] <= offset <= wb["text_offset"]:
            span = wb["text_offset"] - prev["text_offset"]
            if span == 0:
                return wb["audio_offset"] / AUDIO_OFFSET_RESOLUTION
            t0 = prev["audio_offset"] / AUDIO_OFFSET_RESOLUTION
            t1 = wb["audio_offset"] / AUDIO_OFFSET_RESOLUTION
            return t0 + (offset - prev["text_offset"]) / span * (t1 - t0)
        prev = wb

    return word_boundaries[-1]["audio_offset"] / AUDIO_OFFSET_RESOLUTION

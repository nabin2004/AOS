"""Word-level timestamp alignment and Manim Voiceover boundary generator using Kyutai Delayed Streams Modeling.

Converts word timestamps (from Kyutai STT or DSM delay streams) into Manim-compatible
``word_boundaries`` for precise bookmark and kinetic animation synchronization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

AUDIO_OFFSET_RESOLUTION = 10_000_000  # 100ns units used by Manim Voiceover


class WordBoundary(TypedDict):
    audio_offset: int
    text_offset: int
    word_length: int
    text: str
    boundary_type: str


@dataclass
class TimestampedWord:
    text: str
    start_time: float  # in seconds
    end_time: float    # in seconds


def convert_words_to_boundaries(
    words: list[TimestampedWord],
    full_text: str | None = None,
) -> list[WordBoundary]:
    """Convert timestamped words to Manim Voiceover `word_boundaries`.
    
    If `full_text` is provided, character offsets are aligned with `full_text`.
    Otherwise, character offsets are computed sequentially by joining words with spaces.
    """
    boundaries: list[WordBoundary] = [
        {
            "audio_offset": 0,
            "text_offset": 0,
            "word_length": 0,
            "text": "",
            "boundary_type": "Word",
        }
    ]

    current_char_idx = 0
    for w in words:
        word_str = w.text.strip()
        if not word_str:
            continue

        if full_text is not None:
            # Find match in original text starting from current_char_idx
            found_idx = full_text.find(word_str, current_char_idx)
            if found_idx != -1:
                current_char_idx = found_idx
            text_offset = current_char_idx
            current_char_idx += len(word_str)
        else:
            text_offset = current_char_idx
            current_char_idx += len(word_str) + 1

        audio_offset = int(w.start_time * AUDIO_OFFSET_RESOLUTION)
        boundaries.append(
            {
                "audio_offset": audio_offset,
                "text_offset": text_offset,
                "word_length": len(word_str),
                "text": word_str,
                "boundary_type": "Word",
            }
        )

    return boundaries

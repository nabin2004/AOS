from __future__ import annotations

from pathlib import Path

import numpy as np
import scipy.io.wavfile
from manim_voiceover.services.base import SpeechService
from narrator import DEFAULT_VOICE, Narrator

from .speech_markup import (
    build_segment_word_boundaries,
    parse_bookmarks,
)

_narrator: Narrator | None = None
_narrator_voice: str | None = None
_narrator_language: str | None = None


def _get_narrator(voice: str, language: str | None) -> Narrator:
    global _narrator, _narrator_voice, _narrator_language
    if _narrator is None or _narrator_voice != voice or _narrator_language != language:
        _narrator = Narrator(voice=voice, language=language)
        _narrator_voice = voice
        _narrator_language = language
    return _narrator


def _write_concat_wav(
    out_path: Path,
    sample_rate: int,
    chunks: list[np.ndarray],
) -> None:
    if not chunks:
        scipy.io.wavfile.write(out_path, sample_rate, np.zeros(0, dtype=np.float32))
        return
    audio = np.concatenate([np.asarray(c).reshape(-1) for c in chunks], axis=0)
    scipy.io.wavfile.write(out_path, sample_rate, audio)


class AOSSpeechService(SpeechService):
    """Manim Voiceover speech service backed by AOS Pocket TTS (audio_service).

    Bookmarks use segment-split synthesis: text is split at
    ``<bookmark mark='…'/>`` tags, each segment is synthesized with Pocket TTS,
    audio is concatenated, and Manim-compatible ``word_boundaries`` are emitted
    at segment edges so ``wait_until_bookmark`` works without Whisper.
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        language: str | None = None,
        cache_dir: str | Path | None = None,
        **kwargs,
    ):
        super().__init__(cache_dir=cache_dir, **kwargs)
        self.voice = voice
        self.language = language

    def generate_from_text(
        self,
        text: str,
        cache_dir: str | None = None,
        path: str | None = None,
        **kwargs,
    ) -> dict:
        if cache_dir is None:
            cache_dir = self.cache_dir

        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)

        parsed = parse_bookmarks(text)
        config: dict = {"voice": self.voice, "language": self.language}
        if parsed.has_bookmarks:
            config["alignment"] = "segment_split"

        input_data = {
            "input_text": parsed.clean_text,
            "service": "aos",
            "config": config,
        }

        cached = self.get_cached_result(input_data, cache_path)
        if cached is not None:
            return cached

        if path is None:
            audio_path = self.get_audio_basename(input_data) + ".wav"
        else:
            audio_path = path

        narrator = _get_narrator(self.voice, self.language)
        out_file = cache_path / audio_path

        if not parsed.has_bookmarks:
            narrator.synthesize(parsed.clean_text, out_file)
            return {
                "input_text": text,
                "input_data": input_data,
                "original_audio": audio_path,
            }

        chunks: list[np.ndarray] = []
        durations: list[float] = []
        sample_rate = narrator.sample_rate

        for segment in parsed.segments:
            if not segment.strip():
                durations.append(0.0)
                continue
            audio = narrator.synthesize(segment)
            arr = np.asarray(audio).reshape(-1)
            chunks.append(arr)
            durations.append(float(arr.shape[0]) / float(sample_rate))

        _write_concat_wav(out_file, sample_rate, chunks)
        word_boundaries = build_segment_word_boundaries(parsed.segments, durations)

        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
            "word_boundaries": word_boundaries,
        }

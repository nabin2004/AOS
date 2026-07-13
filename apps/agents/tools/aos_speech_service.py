from __future__ import annotations

from pathlib import Path

from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import SpeechService
from narrator import DEFAULT_VOICE, Narrator

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


class AOSSpeechService(SpeechService):
    """Manim Voiceover speech service backed by AOS Pocket TTS (audio_service)."""

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

        input_text = remove_bookmarks(text)
        input_data = {
            "input_text": input_text,
            "service": "aos",
            "config": {"voice": self.voice, "language": self.language},
        }

        cached = self.get_cached_result(input_data, cache_path)
        if cached is not None:
            return cached

        if path is None:
            audio_path = self.get_audio_basename(input_data) + ".wav"
        else:
            audio_path = path

        narrator = _get_narrator(self.voice, self.language)
        narrator.synthesize(input_text, cache_path / audio_path)

        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
        }

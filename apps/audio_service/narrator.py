"""Narration/voice-over generation for AOS videos, backed by Kyutai's Pocket TTS.

Pocket TTS is a 100M-parameter CPU text-to-speech model. `Narrator` keeps the
model and the active voice state resident in memory, since loading either is
the slow part — generating audio for many beats/scenes in a lecture after
that is fast (~6x real-time on CPU).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import scipy.io.wavfile
from pocket_tts import TTSModel, export_model_state

# Built-in voices bundled with Pocket TTS, mapped to their language.
VOICES = {
    "alba": "english",
    "anna": "english",
    "azelma": "english",
    "bill_boerst": "english",
    "caro_davy": "english",
    "charles": "english",
    "cosette": "english",
    "eponine": "english",
    "eve": "english",
    "fantine": "english",
    "george": "english",
    "jane": "english",
    "jean": "english",
    "javert": "english",
    "marius": "english",
    "mary": "english",
    "michael": "english",
    "paul": "english",
    "peter_yearsley": "english",
    "stuart_bell": "english",
    "vera": "english",
    "giovanni": "italian",
    "lola": "spanish",
    "juergen": "german",
    "rafael": "portuguese",
    "estelle": "french",
}

# Pretrained language configs accepted by TTSModel.load_model(language=...).
LANGUAGES = (
    "english_2026-01",
    "english_2026-04",
    "english",
    "french_24l",
    "german_24l",
    "portuguese_24l",
    "italian_24l",
    "spanish_24l",
)

DEFAULT_VOICE = "alba"


class Narrator:
    """Generates narration audio from text using a resident Pocket TTS model."""

    def __init__(self, voice: str | Path = DEFAULT_VOICE, *, language: str | None = None, **model_kwargs):
        self._model = TTSModel.load_model(language=language, **model_kwargs)
        self._voice_state = None
        self.set_voice(voice)

    @property
    def sample_rate(self) -> int:
        return self._model.sample_rate

    def set_voice(self, voice: str | Path) -> None:
        """Switch the active voice.

        Accepts a built-in voice name (see VOICES), a local wav/mp3/safetensors
        path, or an hf://... or https://... URL to a reference clip.
        """
        self._voice_state = self._model.get_state_for_audio_prompt(str(voice))

    def synthesize(self, text: str, out_path: str | Path | None = None):
        """Generate narration audio for `text`.

        Writes a wav file and returns its Path if `out_path` is given;
        otherwise returns the raw audio tensor.
        """
        audio = self._model.generate_audio(self._voice_state, text)
        if out_path is None:
            return audio
        out_path = Path(out_path)
        scipy.io.wavfile.write(out_path, self.sample_rate, audio.numpy())
        return out_path

    def synthesize_stream(self, text: str) -> Iterator:
        """Yield audio chunks as they're generated, for low-latency playback."""
        yield from self._model.generate_audio_stream(self._voice_state, text)

    def synthesize_batch(self, texts: list[str], out_dir: str | Path, prefix: str = "line") -> list[Path]:
        """Narrate multiple lines (e.g. one per beat/scene) with the current
        voice, writing `{prefix}_000.wav`, `{prefix}_001.wav`, ... to out_dir.
        """
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return [self.synthesize(text, out_dir / f"{prefix}_{i:03d}.wav") for i, text in enumerate(texts)]

    def export_voice(self, dest: str | Path) -> Path:
        """Cache the current voice state to a .safetensors file so it can be
        reloaded quickly later via set_voice(dest), skipping re-processing
        of the reference audio.
        """
        dest = Path(dest)
        export_model_state(self._voice_state, dest)
        return dest

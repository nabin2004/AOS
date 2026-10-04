"""Local TTS via Kitten TTS (optional ``tts`` extra)."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol, runtime_checkable


@runtime_checkable
class VoiceOverBackend(Protocol):
    """Pluggable TTS backend (Kitten TTS when the ``tts`` extra is installed)."""

    def synthesize(self, text: str, *, voice: str) -> bytes:
        """Return WAV bytes for ``text`` (sample rate is backend-defined; Kitten uses 24 kHz)."""
        ...


@dataclass(slots=True)
class VoiceOver:
    """Narration clip aligned to the scene timeline."""

    text: str
    voice: str = "Jasper"
    start: float = 0.0

    def synthesize(self, backend: VoiceOverBackend) -> bytes:
        """Render audio using the given backend."""
        return backend.synthesize(self.text, voice=self.voice)


@dataclass(slots=True)
class KittenVoiceOverBackend:
    """Local TTS via Kitten TTS (Apache-2.0).

    ``model_name`` is a Hugging Face Hub repository id (e.g. ``KittenML/kitten-tts-nano-0.8-int8``).
    """

    model_name: str = "KittenML/kitten-tts-nano-0.8-int8"
    speed: float = 1.0
    clean_text: bool = False

    def synthesize(self, text: str, *, voice: str) -> bytes:
        """Synthesize speech to in-memory WAV (24 kHz)."""
        try:
            from kittentts import KittenTTS  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError("Kitten TTS requires the 'tts' extra: uv sync --extra tts") from e
        try:
            import soundfile as sf  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError("soundfile is required with the 'tts' extra for WAV encoding.") from e

        tts = KittenTTS(self.model_name)
        audio = tts.generate(text, voice=voice, speed=self.speed, clean_text=self.clean_text)
        buf = BytesIO()
        sf.write(buf, audio, 24000, format="WAV")
        return buf.getvalue()

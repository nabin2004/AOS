"""Modular Speech Architecture and Dytto Engine for MotionGram and ManimLite.

Supports pluggable, changeable speech models:
- 'edge-tts'   : Ultra-fast Microsoft Edge neural TTS (Christopher, Jenny, etc.)
- 'pocket-tts' : Kyutai Pocket TTS (100M offline CPU model, 24kHz, rich voices: alba, anna, etc.)
- 'dsm'        : Kyutai Delayed Streams Modeling (streaming TTS & STT with word boundaries)
- 'kitten'     : KittenTTS nano model
- 'dytto'      : DiTTo / custom model interface
- 'mock'       : Fast offline stub generating valid WAV tones/silence for headless tests
- 'auto'       : Automatically selects fastest available backend (Edge-TTS -> Pocket TTS -> Mock)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
import wave
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Any

try:
    from manim_voiceover.services.base import SpeechService
except ImportError:

    class SpeechService:  # type: ignore[no-redef]
        """Fallback base class when manim_voiceover is not installed."""

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs


from .dsm_aligner import TimestampedWord, convert_words_to_boundaries

logger = logging.getLogger(__name__)

# =============================================================================
# Audio Utilities & WAV Helpers
# =============================================================================


def get_audio_duration(wav_path: str | Path) -> float:
    """Return the duration of a WAV file in seconds."""
    path = Path(wav_path)
    if not path.is_file():
        return 0.0
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return float(frames) / float(rate) if rate > 0 else 0.0
    except Exception:
        # Fallback to scipy if wave module encounters non-standard header
        try:
            import scipy.io.wavfile

            sr, data = scipy.io.wavfile.read(str(path))
            return float(len(data)) / float(sr) if sr > 0 else 0.0
        except Exception:
            return 0.0


def create_silence_wav(
    out_path: str | Path,
    duration: float = 1.0,
    sample_rate: int = 24000,
) -> Path:
    """Generate a silent standard WAV file."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    num_frames = int(duration * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return path


def clean_bookmarks_from_text(text: str) -> tuple[str, list[tuple[str, int]]]:
    """Remove <bookmark mark='...'/> tags and return cleaned text + (mark, char_idx) pairs."""
    bookmarks: list[tuple[str, int]] = []

    def _repl(match: re.Match[str]) -> str:
        mark_name = match.group(1) or match.group(2)
        # Position is relative to the cleaned text length accumulated so far
        bookmarks.append((mark_name, match.start()))
        return ""

    # Pattern matches <bookmark mark="name"/> and <bookmark mark='name'/>
    cleaned = re.sub(r"""<bookmark\s+mark=(?:["'])(.*?)(?:["'])\s*/>""", _repl, text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, bookmarks


# =============================================================================
# Modular Speech Model Base Class
# =============================================================================


class BaseSpeechModel(ABC):
    """Abstract interface for all modular speech engines in Dytto."""

    name: str = "base"

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if required packages/binaries are installed and available."""
        ...

    @abstractmethod
    def available_voices(self) -> list[str]:
        """List supported voice names for this model."""
        ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Path:
        """Synthesize text to WAV file at out_path."""
        ...

    def synthesize_stream(
        self,
        text: str,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """Stream audio chunks if supported."""
        yield self.synthesize(text, kwargs.get("out_path", "temp.wav"), voice=voice)

    def get_word_boundaries(
        self,
        text: str,
        audio_path: str | Path,
    ) -> list[dict[str, Any]]:
        """Return Manim-Voiceover compatible word_boundaries for text and audio."""
        dur = get_audio_duration(audio_path)
        words = text.split()
        if not words:
            return []

        # Default proportional timing when model does not yield raw word events
        word_dur = dur / max(1, len(words))
        timestamped = [
            TimestampedWord(text=w, start_time=i * word_dur, end_time=(i + 1) * word_dur)
            for i, w in enumerate(words)
        ]
        return convert_words_to_boundaries(timestamped, full_text=text)


# =============================================================================
# Modular Model 1: Edge-TTS (High-Speed Neural Cloud Path)
# =============================================================================


class EdgeTTSSpeechModel(BaseSpeechModel):
    """Microsoft Edge neural TTS engine (fastest, high quality, offline-resilient)."""

    name = "edge-tts"
    DEFAULT_VOICE = "en-US-ChristopherNeural"

    @classmethod
    def is_available(cls) -> bool:
        try:
            import edge_tts  # noqa: F401

            return True
        except ImportError:
            return False

    VOICE_MAP = {
        "alba": "en-US-JennyNeural",
        "anna": "en-US-JennyNeural",
        "cosette": "en-US-JennyNeural",
        "fantine": "en-US-JennyNeural",
        "jane": "en-US-JennyNeural",
        "mary": "en-US-JennyNeural",
        "vera": "en-US-JennyNeural",
        "george": "en-US-GuyNeural",
        "jean": "en-US-ChristopherNeural",
        "javert": "en-US-ChristopherNeural",
        "marius": "en-US-GuyNeural",
        "michael": "en-US-ChristopherNeural",
        "paul": "en-US-GuyNeural",
    }

    def available_voices(self) -> list[str]:
        return [
            "en-US-ChristopherNeural",
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-US-AriaNeural",
            "en-GB-SoniaNeural",
            "en-GB-RyanNeural",
            "fr-FR-DeniseNeural",
            "de-DE-ConradNeural",
            "es-ES-AlvaroNeural",
        ]

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        raw_voice = voice or self.DEFAULT_VOICE
        chosen_voice = self.VOICE_MAP.get(raw_voice.lower(), raw_voice)
        if "-" not in chosen_voice:
            chosen_voice = self.DEFAULT_VOICE

        import edge_tts

        temp_mp3 = out_path.with_suffix(".temp.mp3")

        async def _run() -> None:
            comm = edge_tts.Communicate(text, chosen_voice)
            await asyncio.wait_for(comm.save(str(temp_mp3)), timeout=30.0)

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(lambda: asyncio.run(_run())).result(timeout=35)
            else:
                asyncio.run(_run())

            # Transcode MP3 to standard 24kHz single-channel WAV
            if shutil.which("ffmpeg"):
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(temp_mp3),
                        "-ar",
                        "24000",
                        "-ac",
                        "1",
                        str(out_path),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
            else:
                # Fallback transcode via pydub
                from pydub import AudioSegment

                sound = AudioSegment.from_file(str(temp_mp3))
                sound = sound.set_frame_rate(24000).set_channels(1)
                sound.export(str(out_path), format="wav")

        finally:
            if temp_mp3.is_file():
                import contextlib

                with contextlib.suppress(OSError):
                    temp_mp3.unlink()

        return out_path


# =============================================================================
# Modular Model 2: Pocket TTS (100M Offline CPU Model)
# =============================================================================


class PocketTTSSpeechModel(BaseSpeechModel):
    """Kyutai Pocket TTS engine (100% offline, resident 100M CPU model)."""

    name = "pocket-tts"

    def __init__(self, voice: str = "alba", language: str | None = None) -> None:
        self.default_voice = voice
        self.language = language
        self._narrator = None

    @classmethod
    def is_available(cls) -> bool:
        try:
            import pocket_tts  # noqa: F401
            import scipy.io.wavfile  # noqa: F401

            return True
        except ImportError:
            return False

    def _get_narrator(self, voice: str | None = None) -> Any:
        from .narrator import Narrator

        target_voice = voice or self.default_voice
        if self._narrator is None:
            self._narrator = Narrator(voice=target_voice, language=self.language)
        else:
            self._narrator.set_voice(target_voice)
        return self._narrator

    def available_voices(self) -> list[str]:
        from .narrator import VOICES

        return list(VOICES.keys())

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        narrator = self._get_narrator(voice)
        narrator.synthesize(text, out_path)
        return out_path

    def synthesize_stream(
        self,
        text: str,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        narrator = self._get_narrator(voice)
        yield from narrator.synthesize_stream(text)


# =============================================================================
# Modular Model 3: Kyutai DSM (Delayed Streams Modeling Client)
# =============================================================================


class DSMKyutaiSpeechModel(BaseSpeechModel):
    """Kyutai Delayed Streams Modeling sequence-to-sequence model & client."""

    name = "dsm"

    def __init__(self, server_url: str = "ws://127.0.0.1:8080", voice: str = "alba") -> None:
        self.server_url = server_url
        self.voice = voice

    @classmethod
    def is_available(cls) -> bool:
        try:
            import msgpack  # noqa: F401
            import websockets  # noqa: F401

            return True
        except ImportError:
            return False

    def available_voices(self) -> list[str]:
        return ["expresso", "alba", "anna", "default"]

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Path:
        from .dsm_client import DSMClient

        client = DSMClient(server_url=self.server_url)
        v = voice or self.voice
        return client.synthesize_ws(text, out_path, voice=v)

    def get_word_boundaries(
        self,
        text: str,
        audio_path: str | Path,
    ) -> list[dict[str, Any]]:
        from .dsm_client import DSMClient

        client = DSMClient(server_url=self.server_url)
        try:
            return client.align_audio_for_manim(audio_path, expected_text=text)
        except Exception:
            return super().get_word_boundaries(text, audio_path)


# =============================================================================
# Modular Model 4: KittenTTS (Nano Local TTS)
# =============================================================================


class KittenTTSSpeechModel(BaseSpeechModel):
    """KittenML nano TTS engine."""

    name = "kitten"

    @classmethod
    def is_available(cls) -> bool:
        try:
            import kittentts  # noqa: F401
            import soundfile  # noqa: F401

            return True
        except ImportError:
            return False

    def available_voices(self) -> list[str]:
        return ["Jasper", "Luna", "Bella", "Milo"]

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Path:
        from .voiceover import KittenVoiceOverBackend

        backend = KittenVoiceOverBackend()
        v = voice or "Jasper"
        wav_bytes = backend.synthesize(text, voice=v)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(wav_bytes)
        return out_path


# =============================================================================
# Modular Model 5: Dytto Custom Model / HuggingFace Pipeline
# =============================================================================


class DyttoCustomSpeechModel(BaseSpeechModel):
    """Pluggable Dytto / DiTTo speech model for custom weights and endpoints."""

    name = "dytto"

    def __init__(self, model_id_or_path: str = "dytto-default", voice: str = "alba") -> None:
        self.model_id_or_path = model_id_or_path
        self.voice = voice

    @classmethod
    def is_available(cls) -> bool:
        return True

    def available_voices(self) -> list[str]:
        return ["dytto-natural", "dytto-expressive", "alba", "en-US-ChristopherNeural"]

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Path:
        # Prefer on-device speech for local runs; use cloud Edge-TTS only when
        # Pocket TTS is unavailable and explicitly configured by the caller.
        if PocketTTSSpeechModel.is_available():
            return PocketTTSSpeechModel().synthesize(text, out_path, voice=voice or "alba")
        if EdgeTTSSpeechModel.is_available():
            return EdgeTTSSpeechModel().synthesize(text, out_path, voice=voice or EdgeTTSSpeechModel.DEFAULT_VOICE)
        raise RuntimeError("No speech backend is available; install pocket-tts for local narration.")


# =============================================================================
# Modular Model 6: Mock / Testing Speech Model (Zero external deps)
# =============================================================================


class MockSpeechModel(BaseSpeechModel):
    """Fallback / testing model that generates valid WAV audio without dependencies."""

    name = "mock"

    @classmethod
    def is_available(cls) -> bool:
        return True

    def available_voices(self) -> list[str]:
        return ["mock-voice", "alba", "christopher"]

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        voice: str | None = None,
        **kwargs: Any,
    ) -> Path:
        # Calculate natural speech duration: ~150 words per minute (2.5 words per sec)
        words = text.split()
        dur = max(1.0, len(words) / 2.5)
        return create_silence_wav(out_path, duration=dur)


# =============================================================================
# Dytto Engine & Speech Service
# =============================================================================


class DyttoSpeechService(SpeechService):
    """Central Dytto Narration Engine with modular, changeable speech models.

    Integrates seamlessly with Manim Voiceover, MotionGram, and YAML manifests.
    Allows changing speech models dynamically at runtime.
    """

    MODEL_REGISTRY: dict[str, type[BaseSpeechModel]] = {
        "edge-tts": EdgeTTSSpeechModel,
        "edge": EdgeTTSSpeechModel,
        "pocket-tts": PocketTTSSpeechModel,
        "pocket": PocketTTSSpeechModel,
        "dsm": DSMKyutaiSpeechModel,
        "kyutai": DSMKyutaiSpeechModel,
        "kitten": KittenTTSSpeechModel,
        "kittentts": KittenTTSSpeechModel,
        "dytto": DyttoCustomSpeechModel,
        "ditto": DyttoCustomSpeechModel,
        "mock": MockSpeechModel,
    }

    def __init__(
        self,
        model: str = "pocket-tts",
        voice: str = "alba",
        cache_dir: str | Path = "voiceover_cache",
        sample_rate: int = 24000,
        **kwargs: Any,
    ) -> None:
        model = kwargs.pop("backend", model)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = sample_rate
        self.requested_model = model
        self.voice = voice
        self.kwargs = kwargs
        self._active_model_instance: BaseSpeechModel | None = None
        self._active_model_name: str = ""

        # Initialize requested or auto-resolved model
        self.set_model(model, voice=voice)
        super().__init__(**kwargs)

    @classmethod
    def register_model(cls, name: str, model_cls: type[BaseSpeechModel]) -> None:
        """Register a new modular speech model class."""
        cls.MODEL_REGISTRY[name.lower()] = model_cls

    def set_model(self, model_name: str, voice: str | None = None, **kwargs: Any) -> None:
        """Change the active speech model dynamically."""
        if voice is not None:
            self.voice = voice

        model_key = model_name.lower().strip()
        env_backend = os.getenv("AOS_TTS_BACKEND", "").lower().strip()
        env_dytto = os.getenv("DYTTO_MODEL", "").lower().strip()

        # A caller's explicit model choice always wins. Environment settings
        # only select a backend when the caller requested automatic routing.
        resolved_key = model_key
        if resolved_key in ("auto", ""):
            resolved_key = env_dytto or env_backend or "auto"
        if resolved_key in ("auto", ""):
            if PocketTTSSpeechModel.is_available():
                resolved_key = "pocket-tts"
            elif EdgeTTSSpeechModel.is_available():
                resolved_key = "edge-tts"
            else:
                resolved_key = "mock"

        model_cls = self.MODEL_REGISTRY.get(resolved_key, PocketTTSSpeechModel)
        self._active_model_name = resolved_key
        self._active_model_instance = model_cls(**kwargs)

    @property
    def active_model(self) -> BaseSpeechModel:
        """Return the currently active speech model instance."""
        if self._active_model_instance is None:
            self.set_model(self.requested_model)
        assert self._active_model_instance is not None
        return self._active_model_instance

    @property
    def active_model_name(self) -> str:
        """Return the name of the active speech model."""
        return self._active_model_name

    def available_models(self) -> list[str]:
        """List all registered modular speech model names."""
        return list(self.MODEL_REGISTRY.keys())

    def available_voices(self) -> list[str]:
        """List available voices for the currently active speech model."""
        return self.active_model.available_voices()

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        voice: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> Path:
        """Synthesize text into WAV audio using the active or specified model."""
        if model is not None and model.lower() != self._active_model_name:
            self.set_model(model, voice=voice)
        return self.active_model.synthesize(text, out_path, voice=voice or self.voice, **kwargs)

    def generate_from_text(
        self,
        text: str,
        cache_dir: str | Path | None = None,
        path: str | Path | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Full Manim Voiceover integration contract with bookmark sync."""
        c_dir = Path(cache_dir or self.cache_dir)
        c_dir.mkdir(parents=True, exist_ok=True)

        clean_text, bookmarks_raw = clean_bookmarks_from_text(text)

        # Cache key based on text, active model name, and voice
        text_hash = hash((clean_text, self._active_model_name, self.voice)) & 0xFFFFFFFF
        filename = f"dytto_{self._active_model_name}_{self.voice}_{text_hash:08x}.wav"
        requested_path = Path(path) if path else Path(filename)
        # Manim Voiceover may pass a cache basename or a path containing the
        # cache directory. Always store one canonical file inside cache_dir.
        audio_path = c_dir / requested_path.name
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        if not audio_path.is_file() or audio_path.stat().st_size == 0:
            try:
                self.synthesize(clean_text, audio_path, voice=self.voice)
            except Exception as exc:
                if self._active_model_name != "pocket-tts" and PocketTTSSpeechModel.is_available():
                    logger.warning("TTS backend %s failed; retrying with local Pocket TTS: %s", self._active_model_name, exc)
                    self.set_model("pocket-tts", voice=self.voice)
                    self.synthesize(clean_text, audio_path, voice=self.voice)
                else:
                    raise RuntimeError(
                        f"Speech synthesis failed with {self._active_model_name}; refusing to produce silent narration."
                    ) from exc

        duration = get_audio_duration(audio_path)
        word_boundaries = self.active_model.get_word_boundaries(clean_text, audio_path)

        # Resolve bookmark timestamps accurately based on word boundaries or character position
        bookmark_dict: dict[str, float] = {}
        total_len = max(1, len(clean_text))

        for mark_name, char_pos in bookmarks_raw:
            # Try to match word boundary corresponding to char_pos
            matched_time = None
            for wb in word_boundaries:
                if wb["text_offset"] >= char_pos:
                    matched_time = wb["audio_offset"] / 10_000_000.0
                    break
            if matched_time is None:
                # Proportional offset
                matched_time = (float(char_pos) / float(total_len)) * duration
            bookmark_dict[mark_name] = round(matched_time, 3)

        return {
            # SpeechService._wrap_generate_from_text requires original_audio;
            # VoiceoverScene resolves it relative to speech_service.cache_dir.
            "original_audio": audio_path.name,
            "final_audio": str(audio_path.resolve()),
            "input_text": text,
            "text": clean_text,
            "bookmarks": bookmark_dict,
            "word_boundaries": word_boundaries,
            "duration": duration,
        }


# =============================================================================
# Backward Compatibility & Module Exports
# =============================================================================

# DyttoNarrator and AOSSpeechService are aliases to DyttoSpeechService
DyttoNarrator = DyttoSpeechService
AOSSpeechService = DyttoSpeechService

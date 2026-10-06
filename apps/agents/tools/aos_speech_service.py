from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

try:
    import scipy.io.wavfile
except ImportError:
    scipy = None

try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.base import SpeechService
    VoiceoverSceneFallback = VoiceoverScene
except ImportError:
    from manim import Scene

    class SpeechService:  # type: ignore[no-redef]
        """Fallback base class when manim_voiceover is not installed."""
        def __init__(self, cache_dir: str | Path | None = None, **kwargs: Any):
            self.cache_dir = cache_dir or "voiceover_cache"
            self.kwargs = kwargs

        def get_cached_result(self, input_data: dict, cache_path: Path) -> dict | None:
            return None

        def get_audio_basename(self, input_data: dict) -> str:
            import hashlib, json
            return hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()[:16]

    class VoiceoverTrackerFallback:
        def __init__(self, duration: float = 2.0, bookmarks: dict[str, float] | None = None):
            self.duration = duration
            self.bookmarks = bookmarks or {}

        def get_bookmark_offset(self, mark: str) -> float:
            return self.bookmarks.get(mark, 0.0)

    class VoiceoverContextFallback:
        def __init__(self, scene: Any, text: str, subcaption: str | None = None, **kwargs: Any):
            self.scene = scene
            self.text = text
            self.subcaption = subcaption
            self.kwargs = kwargs
            self.tracker = VoiceoverTrackerFallback(duration=2.0)

        def __enter__(self) -> VoiceoverTrackerFallback:
            speech_service = getattr(self.scene, "speech_service", None)
            if speech_service is not None and hasattr(speech_service, "generate_from_text"):
                try:
                    data = speech_service.generate_from_text(self.text)
                    if isinstance(data, dict):
                        audio_path = data.get("final_audio") or data.get("original_audio")
                        dur = data.get("duration", 2.0)
                        bms = data.get("bookmarks", {})
                        if audio_path and Path(audio_path).exists():
                            try:
                                self.scene.add_sound(str(audio_path))
                            except Exception:
                                pass
                        self.tracker = VoiceoverTrackerFallback(duration=dur, bookmarks=bms)
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).warning("Fallback voiceover audio generation failed: %s", exc)
            return self.tracker

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class VoiceoverSceneFallback(Scene):
        """Fallback implementation when manim_voiceover is not installed."""

        def __init__(self, **kwargs: Any):
            super().__init__(**kwargs)
            self.speech_service = None
            self._current_tracker = None

        def set_speech_service(self, speech_service: Any) -> None:
            self.speech_service = speech_service

        def voiceover(self, text: str = "", **kwargs: Any) -> VoiceoverContextFallback:
            ctx = VoiceoverContextFallback(self, text, **kwargs)
            self._current_tracker = ctx.tracker
            return ctx

        def wait_until_bookmark(self, mark: str) -> None:
            self.wait(0.5)

try:
    from narrator import DEFAULT_VOICE, Narrator
except ImportError:
    try:
        from audio_service.narrator import DEFAULT_VOICE, Narrator
    except ImportError:
        try:
            from apps.audio_service.narrator import DEFAULT_VOICE, Narrator
        except ImportError:
            DEFAULT_VOICE = "alba"
            Narrator = None

from .speech_markup import (
    build_segment_word_boundaries,
    parse_bookmarks,
)

_narrator: Any | None = None
_narrator_voice: str | None = None
_narrator_language: str | None = None


def _get_narrator(voice: str, language: str | None) -> Any:
    global _narrator, _narrator_voice, _narrator_language
    if Narrator is None:
        return None
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
    if scipy is None or not hasattr(scipy, "io") or not hasattr(scipy.io, "wavfile"):
        return
    if not chunks:
        scipy.io.wavfile.write(out_path, sample_rate, np.zeros(0, dtype=np.float32))
        return
    audio = np.concatenate([np.asarray(c).reshape(-1) for c in chunks], axis=0)
    scipy.io.wavfile.write(out_path, sample_rate, audio)


class AOSSpeechService(SpeechService):
    """Manim Voiceover speech service backed by AOS Pocket TTS (audio_service) or Dytto.

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
        backend: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ):
        # An explicit Pocket TTS selection must stay on the local narrator
        # path instead of being interpreted as a Dytto backend name.
        configured_backend = backend or os.getenv("AOS_TTS_BACKEND")
        self.backend = configured_backend.lower() if configured_backend else None
        self.model = model.lower() if isinstance(model, str) else model
        self.voice = voice
        self.language = language
        super().__init__(cache_dir=cache_dir, **kwargs)

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
        # The selected backend comes from the frontend control; do not let a
        # model hint emitted in the storyboard override that choice.
        selected_model = self.backend or self.model
        config: dict = {
            "voice": self.voice,
            "language": self.language,
            "backend": selected_model or "pocket-tts",
            "model": selected_model,
        }
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

        pocket_aliases = {"pocket", "pocket-tts", "pocket_tts"}
        use_pocket = selected_model in pocket_aliases

        # Pocket TTS is native to this service. Other explicit backends, or
        # missing local Pocket TTS support in auto mode, may use Dytto.
        try:
            narrator = _get_narrator(self.voice, self.language) if selected_model != "edge-tts" else None
        except Exception as exc:
            if use_pocket:
                raise RuntimeError(
                    "Pocket TTS was explicitly selected but its local model could not load. "
                    "Check the Pocket TTS installation and model cache in the render environment."
                ) from exc
            raise
        if (selected_model and not use_pocket) or (not selected_model and narrator is None):
            try:
                from motiongram.audio.dytto import DyttoSpeechService
                dytto = DyttoSpeechService(
                    model=selected_model or "auto",
                    voice=self.voice,
                    cache_dir=cache_path,
                )
                return dytto.generate_from_text(text, cache_dir=cache_path, path=path, **kwargs)
            except Exception:
                pass

        if use_pocket and narrator is None:
            raise RuntimeError(
                "Pocket TTS was explicitly selected but is unavailable. "
                "Install the audio-service dependencies, including pocket-tts and scipy."
            )

        narrator = narrator or _get_narrator(self.voice, self.language)
        out_file = cache_path / audio_path

        if narrator is None:
            return {
                "input_text": text,
                "input_data": input_data,
                "original_audio": audio_path,
                "duration": 2.0,
            }

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

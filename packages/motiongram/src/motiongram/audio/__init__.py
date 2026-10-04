"""Audio mixing, voice-over, and Dytto modular narration service."""

from motiongram.audio.dsm_aligner import (
    TimestampedWord,
    WordBoundary,
    convert_words_to_boundaries,
)
from motiongram.audio.dsm_client import DSMClient
from motiongram.audio.dytto import (
    AOSSpeechService,
    BaseSpeechModel,
    DSMKyutaiSpeechModel,
    DyttoCustomSpeechModel,
    DyttoNarrator,
    DyttoSpeechService,
    EdgeTTSSpeechModel,
    KittenTTSSpeechModel,
    MockSpeechModel,
    PocketTTSSpeechModel,
    get_audio_duration,
)
from motiongram.audio.mixer import AudioMixer
from motiongram.audio.narrator import Narrator
from motiongram.audio.voiceover import KittenVoiceOverBackend, VoiceOver, VoiceOverBackend

__all__ = [
    "AOSSpeechService",
    "AudioMixer",
    "BaseSpeechModel",
    "DSMClient",
    "DSMKyutaiSpeechModel",
    "DyttoCustomSpeechModel",
    "DyttoNarrator",
    "DyttoSpeechService",
    "EdgeTTSSpeechModel",
    "KittenTTSSpeechModel",
    "KittenVoiceOverBackend",
    "MockSpeechModel",
    "Narrator",
    "PocketTTSSpeechModel",
    "TimestampedWord",
    "VoiceOver",
    "VoiceOverBackend",
    "WordBoundary",
    "convert_words_to_boundaries",
    "get_audio_duration",
]

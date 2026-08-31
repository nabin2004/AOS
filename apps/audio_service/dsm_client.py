"""Kyutai Delayed Streams Modeling (DSM) Client.

Supports:
1. High-throughput WebSocket streaming to a running Rust `moshi-server` (TTS & STT).
2. In-process PyTorch fallback when `moshi` is installed locally.
3. Native word-level timestamp extraction and Manim Voiceover boundary alignment.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from dsm_aligner import TimestampedWord, convert_words_to_boundaries

SAMPLE_RATE = 24000
FRAME_SIZE = 1920
DEFAULT_VOICE = "expresso/ex03-ex01_happy_001_channel1_334s.wav"
DEFAULT_VOICE_REPO = "kyutai/tts-voices"


class DSMClient:
    """Client for interacting with Kyutai DSM (Rust server or local PyTorch)."""

    def __init__(
        self,
        server_url: str = "ws://127.0.0.1:8080",
        api_key: str = "public_token",
    ):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key

    # =========================================================================
    # WebSocket Streaming (Rust moshi-server)
    # =========================================================================

    async def async_synthesize_ws(
        self,
        text: str,
        out_path: str | Path,
        voice: str = DEFAULT_VOICE,
    ) -> Path:
        """Synthesize audio from text by streaming via Rust moshi-server."""
        import msgpack
        import numpy as np
        import sphn
        import websockets

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        params = {"voice": voice, "format": "PcmMessagePack"}
        uri = f"{self.server_url}/api/tts_streaming?{urlencode(params)}"
        headers = {"kyutai-api-key": self.api_key}

        frames: list[np.ndarray] = []

        async with websockets.connect(uri, additional_headers=headers) as ws:
            async def send_text():
                for word in text.split():
                    await ws.send(msgpack.packb({"type": "Text", "text": word}))
                await ws.send(msgpack.packb({"type": "Eos"}))

            async def receive_audio():
                async for message_bytes in ws:
                    msg = msgpack.unpackb(message_bytes)
                    if msg.get("type") == "Audio":
                        pcm = np.array(msg["pcm"], dtype=np.float32)
                        frames.append(pcm)

            await asyncio.gather(send_text(), receive_audio())

        if not frames:
            raise RuntimeError("No audio received from moshi-server TTS stream.")

        full_pcm = np.concatenate(frames, axis=-1)
        sphn.write_wav(str(out_path), full_pcm, SAMPLE_RATE)
        return out_path

    def synthesize_ws(
        self,
        text: str,
        out_path: str | Path,
        voice: str = DEFAULT_VOICE,
    ) -> Path:
        """Synchronous wrapper for async_synthesize_ws."""
        return asyncio.run(self.async_synthesize_ws(text, out_path, voice))

    async def async_transcribe_ws(
        self,
        audio_path: str | Path,
        rtf: float = 100.0,
    ) -> list[TimestampedWord]:
        """Transcribe audio file with word-level timestamps via Rust moshi-server."""
        import msgpack
        import numpy as np
        import sphn
        import websockets

        audio_path = Path(audio_path)
        pcm_data, _ = sphn.read(str(audio_path), sample_rate=SAMPLE_RATE)
        audio_mono = pcm_data[0]

        uri = f"{self.server_url}/api/asr-streaming"
        headers = {"kyutai-api-key": self.api_key}
        words: list[TimestampedWord] = []

        async with websockets.connect(uri, additional_headers=headers) as ws:
            async def send_audio():
                # 1 second silence prefix for STT initialization
                await ws.send(
                    msgpack.packb(
                        {"type": "Audio", "pcm": [0.0] * SAMPLE_RATE},
                        use_single_float=True,
                    )
                )
                for i in range(0, len(audio_mono), FRAME_SIZE):
                    chunk = audio_mono[i : i + FRAME_SIZE]
                    await ws.send(
                        msgpack.packb(
                            {"type": "Audio", "pcm": [float(x) for x in chunk]},
                            use_single_float=True,
                        )
                    )
                    await asyncio.sleep(0.0001)

                for _ in range(5):
                    await ws.send(
                        msgpack.packb(
                            {"type": "Audio", "pcm": [0.0] * SAMPLE_RATE},
                            use_single_float=True,
                        )
                    )
                await ws.send(
                    msgpack.packb({"type": "Marker", "id": 0}, use_single_float=True)
                )
                for _ in range(35):
                    await ws.send(
                        msgpack.packb(
                            {"type": "Audio", "pcm": [0.0] * SAMPLE_RATE},
                            use_single_float=True,
                        )
                    )

            async def receive_transcripts():
                async for message in ws:
                    data = msgpack.unpackb(message, raw=False)
                    msg_type = data.get("type")
                    if msg_type == "Word":
                        words.append(
                            TimestampedWord(
                                text=data["text"],
                                start_time=float(data["start_time"]),
                                end_time=float(data["start_time"]),
                            )
                        )
                    elif msg_type == "EndWord":
                        if words:
                            words[-1].end_time = float(data["stop_time"])
                    elif msg_type == "Marker":
                        break

            await asyncio.gather(send_audio(), receive_transcripts())

        return words

    def transcribe_ws(
        self,
        audio_path: str | Path,
        rtf: float = 100.0,
    ) -> list[TimestampedWord]:
        """Synchronous wrapper for async_transcribe_ws."""
        return asyncio.run(self.async_transcribe_ws(audio_path, rtf))

    # =========================================================================
    # Manim Voiceover Alignment
    # =========================================================================

    def align_audio_for_manim(
        self,
        audio_path: str | Path,
        expected_text: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get Manim Voiceover compatible word_boundaries from audio transcription."""
        words = self.transcribe_ws(audio_path)
        return convert_words_to_boundaries(words, full_text=expected_text)

"""Mix narration and background audio using pydub."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydub import AudioSegment


@dataclass(slots=True)
class AudioMixer:
    """Combines PCM/WAV segments into a single timeline-aligned track."""

    sample_rate: int = 24000

    def concatenate(self, wav_paths: list[str | Path], out_path: str | Path) -> Path:
        """Concatenate a series of audio files in sequence into a single WAV file."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        combined = AudioSegment.empty()
        for p in wav_paths:
            path = Path(p)
            if path.is_file():
                seg = AudioSegment.from_file(str(path))
                combined += seg
        combined = combined.set_frame_rate(self.sample_rate).set_channels(1)
        combined.export(str(out_path), format="wav")
        return out_path

    def overlay(
        self,
        base_path: str | Path,
        overlay_path: str | Path,
        out_path: str | Path,
        position_ms: int = 0,
    ) -> Path:
        """Overlay an audio track at position_ms milliseconds."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        base = AudioSegment.from_file(str(base_path))
        overlay_seg = AudioSegment.from_file(str(overlay_path))
        mixed = base.overlay(overlay_seg, position=position_ms)
        mixed.export(str(out_path), format="wav")
        return out_path

    def mix(self, segments: list[Any]) -> Any:
        """Return a mixed audio segment."""
        if not segments:
            return None
        combined = AudioSegment.empty()
        for seg in segments:
            if isinstance(seg, (str, Path)):
                p = Path(seg)
                if p.is_file():
                    combined += AudioSegment.from_file(str(p))
            elif isinstance(seg, AudioSegment):
                combined += seg
        return combined

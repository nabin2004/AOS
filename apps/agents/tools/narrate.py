from __future__ import annotations

from pathlib import Path

import scipy.io.wavfile
from pydantic import BaseModel
from pydantic_ai import RunContext

from ir.manim_ir import Scene
from tools.deps import ToolDeps
from tools.registry import aos_toolset

_narrator = None


class BeatNarrationAudio(BaseModel):
    beat_id: str
    wav_path: str
    duration_seconds: float
    text: str


def wav_duration_seconds(path: Path) -> float:
    """Measure wav duration from sample count and sample rate."""
    rate, data = scipy.io.wavfile.read(path)
    n_frames = data.shape[0]
    return round(n_frames / rate, 2)


def _get_narrator():
    """Lazily load the resident Pocket TTS model — loading it is the slow
    part, so we pay that cost once per process, not once per scene."""
    global _narrator
    if _narrator is None:
        from narrator import Narrator

        _narrator = Narrator()
    return _narrator


def narrate_scene(scene: Scene, out_dir: Path) -> list[BeatNarrationAudio]:
    """Synthesize one wav per beat with narration; return paths and measured durations."""
    narrator = _get_narrator()
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[BeatNarrationAudio] = []
    for i, beat in enumerate(scene.beats):
        text = beat.narration.text.strip() if beat.narration else ""
        if not text:
            continue
        wav_path = out_dir / f"{scene.class_name}_{i:02d}.wav"
        narrator.synthesize(text, wav_path)
        results.append(
            BeatNarrationAudio(
                beat_id=beat.id,
                wav_path=str(wav_path),
                duration_seconds=wav_duration_seconds(wav_path),
                text=text,
            )
        )
    return results


def narrate_lecture_scenes(scenes: list[Scene], out_dir: Path) -> list[BeatNarrationAudio]:
    """Synthesize narration for every scene; flat list of per-beat audio metadata."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[BeatNarrationAudio] = []
    for scene in scenes:
        results.extend(narrate_scene(scene, out_dir))
    return results


def narrate_scenes(scenes: list[Scene], out_dir: Path) -> dict[str, list[str]]:
    """Synthesize one wav per beat with narration, grouped by scene class_name."""
    by_scene: dict[str, list[str]] = {}
    for scene in scenes:
        items = narrate_scene(scene, out_dir)
        if items:
            by_scene[scene.class_name] = [item.wav_path for item in items]
    return by_scene


@aos_toolset.tool
def synthesize_scene_narration(
    ctx: RunContext[ToolDeps],
    scene_json: str,
) -> list[BeatNarrationAudio]:
    """Synthesize narration audio for a scene's beats and return wav paths + measured durations."""
    scene = Scene.model_validate_json(scene_json)
    audio_dir = ctx.deps.workspace_dir / "audio"
    return narrate_scene(scene, audio_dir)

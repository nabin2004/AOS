from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import scipy.io.wavfile

from dbos_setup import DBOS

from narrator import DEFAULT_VOICE, Narrator
from tools.coder_workspace import (
    OutputDirError,
    load_manifest,
    record_step,
    resolve_output_dir,
    result_json,
    save_manifest,
)

_narrator: Narrator | None = None
_narrator_voice: str | None = None


def _get_narrator(voice: str) -> Narrator:
    global _narrator, _narrator_voice
    if _narrator is None or _narrator_voice != voice:
        _narrator = Narrator(voice=voice)
        _narrator_voice = voice
    return _narrator


def _slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return (slug[:max_len] or "narration").rstrip("_")


def _wav_duration_seconds(path: Path) -> float:
    rate, data = scipy.io.wavfile.read(path)
    return round(data.shape[0] / rate, 2)


@DBOS.step()
def synthesize_narration(
    text: str,
    voice: str = DEFAULT_VOICE,
    output_dir: str | None = None,
) -> str:
    """Preview narration outside Manim. Writes output_dir/audio/{slug}.wav."""
    text = text.strip()
    if not text:
        return result_json(ok=False, step="narration", error="empty text")

    try:
        workspace = resolve_output_dir(output_dir)
        audio_dir = workspace / "audio"
        audio_dir.mkdir(exist_ok=True)

        wav_path = audio_dir / f"{_slug(text)}.wav"
        _get_narrator(voice).synthesize(text, wav_path)
        duration = _wav_duration_seconds(wav_path)

        manifest = load_manifest(workspace)
        manifest["output_dir"] = str(workspace)
        manifest["last_narration"] = {
            "ok": True,
            "voice": voice,
            "wav_file": str(wav_path.relative_to(workspace)),
            "duration_seconds": duration,
        }
        save_manifest(workspace, manifest)
        record_step(
            workspace,
            "narration",
            {
                "ok": True,
                "wav_file": manifest["last_narration"]["wav_file"],
                "duration_seconds": duration,
            },
        )

        return result_json(
            ok=True,
            step="narration",
            output_dir=str(workspace),
            wav_file=manifest["last_narration"]["wav_file"],
            duration_seconds=duration,
            voice=voice,
            manifest=str(workspace / "manifest.json"),
            message=f"Synthesized narration to {wav_path}.",
        )
    except OutputDirError as e:
        return result_json(
            ok=False,
            step="narration",
            output_dir=output_dir,
            error="invalid_output_dir",
            message=str(e),
        )
    except Exception as e:
        return result_json(
            ok=False,
            step="narration",
            output_dir=output_dir,
            error=str(e),
            message=f"Failed to synthesize narration: {e}",
        )


def voiceover_tools() -> list[Callable[..., str]]:
    return [synthesize_narration]

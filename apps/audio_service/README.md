# audio_service

Narration/voice-over generation for AOS videos, backed by Kyutai's Pocket TTS — a
100M-parameter text-to-speech model that runs on CPU (~6x real-time, no GPU
required).

`narrator.py` wraps Pocket TTS in a `Narrator` class that keeps the model and the
active voice resident in memory, so once loaded, generating audio per beat/scene
in a lecture is fast.

## Install

```bash
uv sync --package audio-service
```

## Quick start

```python
from narrator import Narrator

narrator = Narrator(voice="alba")
narrator.synthesize("Hello world, this is a test.", "output.wav")
```

Run the bundled demo:

```bash
uv run --package audio-service python apps/audio_service/main.py
```

## API

| Method | Purpose |
| --- | --- |
| `Narrator(voice="alba", language=None, **model_kwargs)` | Load the model once and set the initial voice |
| `.sample_rate` | Output sample rate in Hz (typically 24000) |
| `.set_voice(voice)` | Switch voice without reloading the model |
| `.synthesize(text, out_path=None)` | Generate audio for one line; writes a wav if `out_path` is given, otherwise returns the raw tensor |
| `.synthesize_stream(text)` | Yield audio chunks as they're generated, for low-latency playback |
| `.synthesize_batch(texts, out_dir, prefix="line")` | Narrate a list of lines (one per beat/scene) to `{prefix}_000.wav`, `{prefix}_001.wav`, ... |
| `.export_voice(dest)` | Cache the current voice state to `.safetensors` for fast reload later via `set_voice(dest)` |

`voice` accepts a built-in voice name (see below), a local wav/mp3/safetensors path,
or an `hf://...` / `https://...` URL to a reference clip for voice cloning.

## Narrating a lecture

`synthesize_batch` maps directly onto AOS's beat/scene structure — narrate each
beat's script line with the same voice in one call:

```python
narrator = Narrator(voice="alba")
narration_paths = narrator.synthesize_batch(
    [beat.narration for beat in lecture.beats],
    out_dir="workspace/narration",
)
```

For a voice that will be reused across many lecture generations, export it once
and reload it from disk instead of re-processing the reference clip every run:

```python
narrator.export_voice("voices/alba.safetensors")
# later, in a new process:
narrator.set_voice("voices/alba.safetensors")
```

## Built-in voices

| Voice | Language |
| --- | --- |
| alba, anna, azelma, bill_boerst, caro_davy, charles, cosette, eponine, eve, fantine, george, jane, jean, javert, marius, mary, michael, paul, peter_yearsley, stuart_bell, vera | english |
| giovanni | italian |
| lola | spanish |
| juergen | german |
| rafael | portuguese |
| estelle | french |

## Languages

Pass `language=` to `Narrator(...)` to pick the underlying model:
`english_2026-01`, `english_2026-04`, `english` (default), `french_24l`, `german_24l`,
`portuguese_24l`, `italian_24l`, `spanish_24l`. The `_24l` variants are larger,
higher-quality, and slower — useful when narration quality matters more than
generation speed.

## Notes

- Requires PyTorch 2.5+ (CPU build is fine, no GPU needed).
- The Pocket TTS CLI (`pocket-tts generate` / `pocket-tts serve`) is still available
  for quick manual experimentation with voices and prompts outside this service.
- Clean voice reference clips before using them for cloning — Pocket TTS reproduces
  the reference audio's quality, noise included.

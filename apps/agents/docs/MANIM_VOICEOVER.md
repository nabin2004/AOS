# Manim Voiceover + AOS Audio Service

This guide explains how the **coder agent** adds narration directly inside Manim scenes using [Manim Voiceover](https://voiceover.manim.community/en/stable/), backed by our local Pocket TTS stack in [`apps/audio_service`](../../audio_service/narrator.py).

## Why AOSSpeechService?

Manim Voiceover supports many cloud speech services (Azure, OpenAI, ElevenLabs, etc.). AOS uses **`AOSSpeechService`** instead:

- Runs **offline** on CPU via Pocket TTS
- **Free** — no API keys or accounts
- Same `Narrator` engine as the main lecture pipeline (`tools/narrate.py`)

## Workspace layout

All coder tools share one folder (default: `workspace/coder/`):

```
workspace/coder/
  scene.py              # Manim source
  manifest.json         # structured run history
  logs/compile.log      # manim stdout/stderr
  audio/                # preview wavs from synthesize_narration
  voiceover_cache/      # manim-voiceover cache (wav + cache.json)
  media/                # rendered video output
```

## Agent tools

| Tool | Purpose |
| --- | --- |
| `manim_write(code, scene_name, output_dir)` | Write scene source to the workspace |
| `compile_manim_code(code, scene_name, output_dir)` | Render scene via `uv run manim` |
| `synthesize_narration(text, voice, output_dir)` | Preview narration wav without rendering |
| `search_manim_docs` / `search_manim_signatures` | Look up Manim API docs |

All tools return **JSON** with `ok`, paths, and status. Check `manifest.json` for the full history.

## Minimal voiceover scene

```python
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService


class IntroScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )

        circle = Circle()
        with self.voiceover(text="This circle is drawn as I speak.") as tracker:
            self.play(Create(circle), run_time=tracker.duration)
```

Compile from the agents directory:

```bash
cd apps/agents
uv run python -c "
from tools.compile import compile_manim_code
print(compile_manim_code(open('workspace/coder/scene.py').read(), 'scene'))
"
```

## Available voices

Built-in Pocket TTS voices (see `narrator.VOICES`):

- **English:** `alba` (default), `anna`, `charles`, `mary`, `michael`, and others
- **Other languages:** `giovanni` (IT), `lola` (ES), `juergen` (DE), `rafael` (PT), `estelle` (FR)

Pass the voice name to both `AOSSpeechService(voice="alba")` and `synthesize_narration(text, voice="alba")`.

## How it works

1. The coder agent writes a `VoiceoverScene` that calls `self.set_speech_service(AOSSpeechService(...))`.
2. Each `with self.voiceover(text="...")` block triggers `AOSSpeechService.generate_from_text()`.
3. `AOSSpeechService` calls `Narrator.synthesize()` and writes a `.wav` into `voiceover_cache/`.
4. Manim Voiceover plays the audio and syncs animation timing via the tracker (`tracker.duration`).
5. `compile_manim_code` runs `uv run manim` so `tools.aos_speech_service` is importable from the workspace.

## Scope

This integration is for the **coder agent workspace** only. The main lecture pipeline still uses post-render narration via `tools/narrate.py` and `tools/assemble.py`. Docker render (`tools/render.py`) does not run voiceover scenes in this pass.

## Further reading

- [Manim Voiceover docs](https://voiceover.manim.community/en/stable/)
- [Speech services comparison](https://voiceover.manim.community/en/stable/services.html)
- [Quickstart](https://voiceover.manim.community/en/stable/quickstart.html)

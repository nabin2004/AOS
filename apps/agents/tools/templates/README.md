# Manim templates (AOS)

Editable domain plugins for the agents environment. I keep the long-form notes here:

**→ [Developer guide: plugins, extending, agents & finetuning](../../docs/MANIM_PLUGINS.md)**

Also: [Voiceover + AOS TTS](../../docs/MANIM_VOICEOVER.md).

| Folder | Package | Use |
|--------|---------|-----|
| `viz/` | `manim_viz` | Shared primitives + concept registry |
| `math/` | `manim_math` | Maths / linalg / calculus |
| `physics/` | `manim_physics` | HS mechanics |
| `dsa/` | `manim_dsa` | Algorithms & data structures |
| `ai/` | `manim_ai` | Deep learning curriculum |
| `chess/` | `manim_chess` | 2D chess board (python-chess) |
| `deeplearning/` | `manim_deeplearning` | Legacy thin helpers (prefer `manim_ai`) |

Install: declared in `apps/agents/pyproject.toml` as editable path deps. From `apps/agents`:

```bash
uv sync
uv run manim -ql tools/templates/math/demos/demo_derivative.py DemoDerivative
```

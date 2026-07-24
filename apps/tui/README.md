# tui

Educlaw-style Typer CLI for AOS — animated logo, sub-commands, and a local lecture/course library.

```bash
uv run --package tui aos-tui
# or
uv run --package tui python apps/tui/run.py
```

## Commands

| Command | Description |
|---------|-------------|
| `aos-tui` | Animated logo + help |
| `aos-tui chat` | Interactive `>` prompt loop |
| `aos-tui doctor` | Check assets and store paths |
| `aos-tui lecture plan\|generate` | Single-lecture pipeline (stubs) |
| `aos-tui course plan\|generate` | Course pipeline (stubs) |
| `aos-tui anim plan\|render` | Manim planning/rendering (stubs) |
| `aos-tui library …` | Browse/create/play saved content via `store` |

## Examples

```bash
aos-tui doctor
aos-tui chat
aos-tui library list lectures
aos-tui library create lecture "Intro to calculus" --subject math --duration 10
aos-tui library search lectures calculus
aos-tui library play <id>
aos-tui lecture plan -p "Gradient descent"
aos-tui course generate -p "Linear algebra" --lectures 4
```

[`apps/cli.py`](../cli.py) exposes the same store operations under a flatter `aos` command tree. `aos-tui` is the educlaw-style superset with pipeline stubs to wire later.

Extend pipeline commands in [`tui/cli.py`](tui/cli.py) where `# TODO` comments appear.

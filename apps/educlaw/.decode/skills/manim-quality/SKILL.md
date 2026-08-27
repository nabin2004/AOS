---
name: manim-quality
description: Choose Manim render quality flags for Docker (-ql/-qm/-qh). Use when rendering or debugging a slow scene.
---

# Render quality

`manim_render` maps `quality` to `manim -q{l|m|h|k}` inside `manimcommunity/manim`.

| Flag | Use |
|------|-----|
| `l` | Preview / iterate (default for debugging) |
| `m` | Default EduClaw quality |
| `h` | Final-ish local check |
| `k` | 4K — avoid unless requested |

Docker preview flags `-p` and `-f` are not supported in the container. Write media under the mounted workspace (`/manim`).

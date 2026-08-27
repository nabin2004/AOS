---
name: manim-latex
description: LaTeX and ctex notes for the official Manim Docker image. Use when Tex or Chinese typesetting fails.
---

# LaTeX in the Manim Docker image

`manimcommunity/manim` ships a **minimal TeX Live**. `ctex` is not installed.

If a scene uses `TexTemplateLibrary.ctex` or CJK fonts, install inside a durable container (not the throwaway `docker run --rm` path):

```text
tlmgr install ctex
```

Prefer `MathTex` / `Tex` with default templates first. Do not assume host TeX is visible — only the container toolchain runs.

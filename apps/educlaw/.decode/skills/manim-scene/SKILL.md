---
name: manim-scene
description: Start a Community Manim scene (Scene subclass, construct, Circle/Text). Use when writing a new animation file.
---

# Manim scene template

```python
from manim import *


class Intro(Scene):
    def construct(self):
        title = Text("Hello")
        self.play(Write(title))
        self.wait(0.5)
```

Rules:

- Import `from manim import *` (Community edition).
- One public `Scene` subclass per file unless the user asks otherwise.
- Keep the first scene under 15 seconds (`self.wait` totals).
- After writing, call `syntax_check` / rely on write diagnostics before `manim_render`.

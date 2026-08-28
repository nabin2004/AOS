# Using aos-manim-slides

Declarative presentation engine for Manim: you describe **what** is on a slide; the layout engine decides **where** it goes. Animation stays procedural (Manim `play`). Body and title type use **Computer Modern** via Manim `Tex`.

## Install

The plugin depends on `manim` and `aos-manim-core`. From the monorepo (editable):

```bash
pip install -e aos-manim-core
pip install -e aos-manim-slides
```

Optional speech (manim-voiceover, not a built-in TTS engine):

```bash
pip install -e "aos-manim-slides[voiceover]"
```

See [03-voiceover.md](03-voiceover.md) for bookmarks, speech services, and `enable_voiceover`.

## Two authoring paths

| Path | Use when | Entry points |
|---|---|---|
| Declarative | Deterministic layout, overflow, auto voiceover cues | `Slide.from_markdown`, `Slide.deck_from_markdown`, `Slide.from_spec` |
| Lecture templates | Hand-timed beats (`play_on`, `beats`) | `BrandingIntro`, `BulletBoard`, `CopyExplain`, … |

You can mix them in one scene: show a Markdown deck, then swap in a `CopyExplain` panel.

## Scenes

```python
from aos_manim_core import set_theme
from aos_manim_slides import Slide, SlideScene, VoiceoverSlideScene

class MyDeck(VoiceoverSlideScene):
    def construct(self):
        set_theme("academic_oxford")
        for slide in Slide.deck_from_markdown(markdown):
            self.show_slide(slide, transition="fade", lecture=True)
            self.pause_slide(0.4)
```

- `SlideScene.show_slide(slide, transition="fade", run_time=0.8, lecture=False)` — `lecture=False` by default.
- `VoiceoverSlideScene.show_slide(...)` — same API, `lecture=True` by default (hide cueable body, then reveal on cues).
- Transitions: `"fade"`, `"wipe"`, `"zoom"`. Anything else replaces the old slide without a transition.
- `pause_slide(duration=1.0)` waits between slides.
- `lecture_gap` (default `0.35` on `VoiceoverSlideScene`) is the wait between cues when voiceover is off.

Themes come from core, not from slides config:

```python
from aos_manim_core import set_theme, use_theme

set_theme("academic_oxford")  # modern_dark, nord, cyberpunk, …
with use_theme("nord"):
    slide = Slide.from_spec(spec)
```

## Markdown decks

Decks are Marp-like: YAML frontmatter, `---` between slides, `#` titles, lists, math, fences.

````markdown
---
footer: AOS Manim Slides
---

---
layout: title
title: Iterative Methods
subtitle: Gradient descent, Newton, and search
author: AOS Manim
date: 2026
---

# Iterative Methods

---
layout: two-column
title: Gradient Descent
voiceover: |
  We minimize a smooth objective.
  <bookmark mark='eq0'/>The update follows the negative gradient.
---

# Gradient Descent

We want to minimize:

$$
f(x) = x^2
$$

```diagram
gradient_descent(f=x**2, x=1.5)
```

> Move in the direction of the negative gradient.
````

Load a whole file:

```python
from pathlib import Path
from aos_manim_slides import Slide, VoiceoverSlideScene

markdown = Path("slides/calculus_methods.md").read_text(encoding="utf-8")

class DeclarativeMethodsScene(VoiceoverSlideScene):
    def construct(self):
        for slide in Slide.deck_from_markdown(markdown):
            self.show_slide(slide, transition="fade", lecture=True)
            self.pause_slide(0.4)
```

A single slide: `Slide.from_markdown(text)`.

### Frontmatter keys

Slide-level keys map onto `SlideSpec`:

| Key | Meaning |
|---|---|
| `layout` | Recipe name (default `title-content`) |
| `title`, `subtitle` | Chrome / first `#` heading can also set `title` |
| `author`, `affiliation`, `date` | Title-slide metadata |
| `section_number` | Section badge |
| `footer` | Footer string (deck-level footer is inherited) |
| `voiceover` | Authored narration (`|` multiline YAML) |
| `ratios` | Column width ratios, e.g. `[0.42, 0.58]` |

A first chunk that is **only** YAML (no body, no slide keys) is treated as **global defaults** (`footer`, presentation `title`). Later slides merge those defaults.

Quiz fields (`question`, `options`, `correct_index`, `explanation`) are Python/`SlideSpec` today; they are not parsed from Markdown frontmatter.

### Markdown grammar

| Construct | Becomes |
|---|---|
| `# Heading` | Slide `title` if unset; `##`+ → `Heading` |
| Paragraphs | `Paragraph` |
| `- ` / `* ` / `1. ` lists | `ListBlock` |
| `$$ ... $$` | `Equation` |
| `> quote` | `Callout(title="Note", body=...)` |
| `![caption](path)` | `ImageBlock` |
| `` ```diagram `` / `` ```aos-diagram `` | `DiagramRef` |
| `` ```animation `` / `` ```aos-animation `` | `AnimationSlot` |
| other `` ```lang `` | `CodeBlock` |
| `:::diagram` / `:::animation` / `:::callout` | Same as fences; callout can use `title:` / `body:` YAML inside |

Fence call syntax (first line):

```text
gradient_descent(f=x**2, x=1.5)
newton_method(f=x**2-2, x0=1.5)
lorenz(sigma=10, rho=28, beta=2.667)
```

A positional argument without `=` is stored as `f`. Extra lines after the call become `kwargs["body"]`.

## Python (`SlideSpec`)

```python
from aos_manim_slides import (
    Slide,
    SlideSpec,
    Paragraph,
    Equation,
    DiagramRef,
    ListBlock,
    Callout,
)

slide = Slide.from_spec(SlideSpec(
    title="Gradient Descent",
    layout="two-column",
    left=[
        Paragraph("We minimize a function"),
        Equation(r"x_{n+1}=x_n-\eta\nabla f(x_n)"),
    ],
    right=[DiagramRef("gradient_descent", kwargs={"f": "x**2"})],
))
```

Convenience templates (they build a `SlideSpec` for you):

```python
from aos_manim_slides import TitleSlide, SectionSlide, ContentSlide, TwoColumnSlide, QuizSlide

TitleSlide("Iterative Methods", subtitle="…", author="AOS", date="2026")
SectionSlide("Optimization", section_number=1)
ContentSlide("Agenda", bullets=["Define the field", "Show the flow"], callout=("Note", "Keep it short"))
TwoColumnSlide("Compare", left_vgroup, right_vgroup)  # wraps RawMobject
QuizSlide("What is the update?", ["SGD", "Newton", "Both"], correct_index=0)
```

`SlideSpec` fields worth knowing: `blocks`, `left`/`right`, `columns`, `ratios`, `voiceover`, `cues`. Content units: `Paragraph`, `Heading`, `Equation`, `CodeBlock`, `Callout`, `ListBlock`, `DiagramRef`, `AnimationSlot`, plus `ImageBlock` / `RawMobject` / `ColumnGroup` on the document model (`from aos_manim_slides.document import RawMobject`).

## Layouts

`VALID_LAYOUTS`:

`title`, `title-content`, `two-column`, `three-column`, `image-text`, `text-image`, `full-screen`, `comparison`, `equation-focus`, `diagram-focus`, `code-focus`, `quiz`, `section`.

On a ~4:3 frame, column recipes collapse to a vertical stack. Overflow retries in priority order (see [02-best-practices.md](02-best-practices.md)).

## Render

From the repo root (PowerShell):

```powershell
& .venv\Scripts\manim -ql examples/declarative_deck.py DeclarativeMethodsScene
& .venv\Scripts\manim -ql examples/ecosystem_lecture.py AOSEcosystemLecture
& .venv\Scripts\manim -ql -s examples/demo_presentation.py AOSComprehensiveDemoScene
```

Scene class in `examples/declarative_deck.py` is `DeclarativeMethodsScene`. Preview with `-pql` if you want the player.

## Next

- [Best practices](02-best-practices.md)
- [Voiceover](03-voiceover.md)
- [Visualizations](04-visualizations.md)
- [Components and plugins](05-components-and-plugins.md)

# aos-manim-slides

Declarative presentation engine for Manim: you describe **what** is on a slide; the plugin decides **where** it goes. Animation stays procedural. Body and title type use **Computer Modern** (Manim `Tex`).

## Install

```bash
pip install -e aos-manim-core
pip install -e aos-manim-slides
pip install -e "aos-manim-slides[voiceover]"   # optional; manim-voiceover
```

## Start here

```python
from aos_manim_core import set_theme
from aos_manim_slides import Slide, VoiceoverSlideScene

class MyDeck(VoiceoverSlideScene):
    def construct(self):
        set_theme("academic_oxford")
        for slide in Slide.deck_from_markdown(markdown):
            self.show_slide(slide, transition="fade", lecture=True)
            self.pause_slide(0.4)
```

Layouts: `title`, `title-content`, `two-column`, `three-column`, `image-text`, `text-image`, `full-screen`, `comparison`, `equation-focus`, `diagram-focus`, `code-focus`, `quiz`, `section`.

## Guide

1. [Usage](docs/01-usage.md) — install, scenes, Markdown grammar, `SlideSpec`, render
2. [Best practices](docs/02-best-practices.md) — typography, packing, overflow, Slide vs lecture
3. [Voiceover](docs/03-voiceover.md) — bookmarks, auto-script, `beats`, manim-voiceover
4. [Visualizations](docs/04-visualizations.md) — diagrams, animation slots, `RawMobject`, Cueable
5. [Components and plugins](docs/05-components-and-plugins.md) — cards, lecture boards, maths/physics/code/beamer

## Render

```bash
manim -pql examples/declarative_deck.py DeclarativeMethodsScene
```

From the monorepo root, the scene class is `DeclarativeMethodsScene`. `VoiceoverSlideScene` subclasses `SlideScene`. Call `show_slide(slide, lecture=True)` (default on the voiceover scene) to hide body, then reveal on bookmarks.

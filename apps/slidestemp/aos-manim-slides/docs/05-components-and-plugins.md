# Components and other plugins

UI chrome lives in slides. STEM and reasoning visuals live in sibling packages. Compose them with lecture templates, `RawMobject`, or the diagram registry. Always resolve color from `aos_manim_core` themes.

## UI components

From `aos_manim_slides`: `Card`, `Badge`, `CalloutBox`.

```python
from aos_manim_slides import Card, Badge, CalloutBox

card = Card(width=6.0, height=4.0)  # theme.surface / theme.border
badge = Badge("STEM", font_size=16)  # pill, theme.primary
note = CalloutBox("Note", "Move along the negative gradient.", width=6.5, height=2.0)
```

| Class | Role | Useful params |
|---|---|---|
| `Card` | Rounded surface | `width`, `height`, `corner_radius`, `fill_color`, `stroke_color`, `theme` |
| `Badge` | Pill label (`slide_tex`) | `text`, `color`, `text_color`, `font_size` |
| `CalloutBox` | Card + left accent bar + title/body | `title`, `body`, `width`, `height`, `accent_color` |

Markdown `>` lines and `:::callout` become AST `Callout` (layout builders, not necessarily `CalloutBox`). Imperative extras after layout:

```python
slide = Slide.from_spec(spec)
slide.add_content(Badge("Draft"))
```

## Lecture templates

Construct → `scene.add` (or swap) → `play_on(scene)` or per-beat methods + `beats(...)`.

| Template | Behavior |
|---|---|
| `BrandingIntro` | Brand mark morphs into lecture title |
| `QuoteCard` | Quote, rule, author |
| `DisclaimerCard` | Warning title + highlighted lines |
| `BulletBoard` | Title + sequential bullets; cue ids `li0…`; `voiceover_script()` |
| `TwoColumnBullets` | Row-by-row two columns; `play_row`, `row_count` |
| `CopyExplain` | Left bullets, `TransformFromCopy` into right-hand diagrams |
| `CodeReveal` | `Create` a listing; `highlight_line(scene, n)` if the listing is Cueable |

```python
from aos_manim_slides import BrandingIntro, BulletBoard, CopyExplain, VoiceoverSlideScene

class Open(VoiceoverSlideScene):
    def construct(self):
        intro = BrandingIntro(
            brand="AOS Manim",
            byline="Eight plugins. One theme.",
            lecture_title="Seeing the Computation",
            subtitle="Models, motion, molecules, and proofs",
        )
        self.add(intro)
        intro.play_on(self)

        board = BulletBoard("Agenda", ["Define the field", "Show the flow"])
        self.add(board)
        board.play_on(self)
```

`CopyExplain(title, items, diagrams)` expects one diagram per copy index for `play_copy(scene, i)`. Hide diagrams (`set_opacity(0)`) before `beats` if you want bookmarks to drive the copy.

Helpers also exported: `play_bullets`, `play_column_rows`.

## Recipe: include another plugin

1. `set_theme(...)` so maths/physics/code match the slide.
2. Build the plugin mobject (`DerivativeVisualizer`, `Molecule2DMobject`, …).
3. Place it:
   - `CopyExplain(..., [graph])` for lecture copy-to-plot
   - `RawMobject` / `TwoColumnSlide` for declarative packing
   - `register_diagram("name", factory)` for Markdown decks
4. Drive it: `show_slide(..., lecture=True)` or `beats([(mark, fn), ...])`.

Reference implementation: `examples/ecosystem_lecture.py`.

## Sibling plugins

### aos-manim-maths

```python
from aos_manim_maths import DerivativeVisualizer, RootFindingVisualizer

vis = DerivativeVisualizer()
packed = vis.build_derivative_mobjects("x**2 - 2*x", 2.0, axes_width=5.0, axes_height=3.0)
graph = VGroup(packed["axes"], packed["curve"], packed["tangent_line"], packed["point"])

newton = RootFindingVisualizer().build_cueable_root_finding(
    "x**2 - 2", 1.5, axes_width=5.0, axes_height=3.0, show_all_steps=False
)
```

Same plots via `gradient_descent` / `newton_method` diagram names.

### aos-manim-physics

```python
from aos_manim_physics import ProjectileVisualizer

packed = ProjectileVisualizer().build_projectile_mobjects(
    v0=20.0, theta_deg=45.0, axes_width=5.2, axes_height=3.0
)
```

### aos-manim-chemistry

```python
from aos_manim_chemistry import Molecule2DMobject

water = Molecule2DMobject.create_water().scale(1.25)
```

### aos-manim-algorithms

```python
from aos_manim_algorithms import BinarySearchVisualizer
# or Markdown: ```diagram / binary_search(arr=[1,3,4,7], target=7)
```

### aos-manim-code

```python
from aos_manim_code import CodeWindow
from aos_manim_slides import CodeReveal

listing = CodeWindow(source, language="python")  # API as in that package
panel = CodeReveal(listing, title="Binary search")
panel.play_on(self)
panel.highlight_line(self, 3)
```

### aos-manim-proofs

```python
from aos_manim_proofs import DerivationChain, ProofStep, StepType
```

Place the chain in `CopyExplain` or `RawMobject` like any other `VGroup`.

### aos-manim-beamer

Layer A sibling: Beamer-style frames next to (or instead of) `Slide`.

```python
from aos_manim_beamer import AlertBlock, BeamerFrame, ExampleBlock, BeamerBulletFrame
```

Use `AlertBlock` / `ExampleBlock` as lecture chrome; do not mix Beamer coordinate systems with `LayoutEngine` unless you wrap the block as a `RawMobject` inside a `SlideSpec`.

## Themes

```python
from aos_manim_core import set_theme, use_theme, get_theme

set_theme("academic_oxford")
self.camera.background_color = get_theme().background

with use_theme("nord"):
    slide = Slide.from_spec(spec)
```

No plugin should hardcode hex colors for body chrome; pass `theme=` only when you need a one-off override on `Card` / visualizers.

## Public slides API (quick list)

Scenes: `SlideScene`, `VoiceoverSlideScene`  
Slide: `Slide`, `TitleSlide`, `SectionSlide`, `ContentSlide`, `TwoColumnSlide`, `QuizSlide`  
AST: `SlideSpec`, `Presentation`, `Paragraph`, `Heading`, `Equation`, `CodeBlock`, `Callout`, `DiagramRef`, `AnimationSlot`, `ListBlock`, `parse_markdown`, `parse_slide_markdown`  
Layout: `LayoutEngine`, `LayoutReport`, `VStack`, `HStack`, `Grid`, `Overlay`, `Center`, `Align`, `Padding`, `Box`, `Rect`  
Diagrams: `build_diagram`, `build_animation`, `register_diagram`, `register_animation`, `DiagramNotFoundError`  
Narration: `assign_content_ids`, `auto_script_from_spec`, `script_for_slide`  
Lecture: `BrandingIntro`, `BulletBoard`, `CodeReveal`, `CopyExplain`, `DisclaimerCard`, `QuoteCard`, `TwoColumnBullets`  
UI: `Card`, `Badge`, `CalloutBox`  
Transitions: `fade_transition`, `wipe_transition`, `zoom_slide_transition`

`RawMobject` / `ImageBlock`: `from aos_manim_slides.document import RawMobject`.

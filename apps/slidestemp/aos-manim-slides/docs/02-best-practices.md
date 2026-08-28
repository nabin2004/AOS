# Best practices

These rules are encoded in the layout engine, typography helpers, and the existing README. Follow them so decks stay readable and cueable.

## Declarative content, procedural animation

The AST (`SlideSpec`, Markdown) describes **what** is on the slide. You still animate with Manim (`play`, transitions, `beats`). Do not encode pixel coordinates in the spec: `Block` has `role` / `priority` / `span`, never screen position.

## Typography

Titles, bullets, and body copy go through `aos_manim_slides.typography.slide_tex`, which renders Computer Modern via `Tex`.

- If LaTeX is missing, it falls back to Manim `Text` **without** a custom `font=` (never Sans).
- Equations stay `MathTex` (`Equation` blocks / `$$`).
- Code stays monospace (`CodeBlock`, `CodeWindow`).
- Do not pass a UI font name on slide body text; theme tokens already pick sizes and colors.

## Packing

Content is packed from the **top-left** of the content rectangle. Leftover height stays at the **bottom**. Do not expect items to be vertically centered as a group.

- **Title slides:** title and subtitle in the upper left; author, affiliation, and date in the lower left.
- **Section slides:** badge and heading upper-left, not a tight centered stack.
- **Equations and diagrams:** centered in their own cell (`equation-focus`, `diagram-focus`, column cells).
- **Lecture templates:** chrome pinned to top/left with extra gap under titles (`BulletBoard`, `TwoColumnBullets`, `BrandingIntro`).

## Overflow and 4:3

The overflow solver retries in this order (`TACTIC_ORDER`):

1. Drop decorations (callouts with `role="decoration"`)
2. Shrink body font (down to a floor of 16)
3. Collapse columns to a stack
4. Scale diagrams
5. Reduce equations
6. Reduce title

Column recipes collapse on a ~4:3 frame even before overflow. After layout, inspect `slide.layout_report` (`attempts`, `tactics`, `overflow_cleared`, `issues`). `SlideOverflowValidator` and core `CanvasBoundsValidator` catch clipping.

If a slide still overflows: fewer bullets, `diagram-focus` instead of stuffing a plot into a narrow column, or split into two slides.

## Animation slots, not hard-coded sims

Do not put a Lorenz integrator (or any heavy sim) in the slide AST. Reserve a diagram-sized region with `AnimationSlot` / `` ```animation `` and `register_animation` when the factory exists. Unknown names still layout as a labeled frame, so decks parse before the visualizer is ready. See [04-visualizations.md](04-visualizations.md).

## Cueable visualizers

If a diagram should step with narration, implement the Cueable contract (`cue_targets`, `apply_cue`, `step_count`, often `play_on`). Auto-scripts then emit `d0s0`, `d0s1`, … `STEP` cues. Plain `VGroup`s only get a single `REVEAL`.

## Slide vs lecture templates

| Path | Use when |
|---|---|
| `Slide` / Markdown / `SlideSpec` | Deterministic packing, overflow, bookmark IDs (`li0`, `eq0`, `d0`) |
| `BrandingIntro`, `BulletBoard`, `QuoteCard`, `TwoColumnBullets`, `CopyExplain`, `CodeReveal`, `DisclaimerCard` | Hand-timed lecture beats with `play_on(scene)` or `VoiceoverSlideScene.beats(...)` |

Use Markdown for method decks (calculus, comparison). Use lecture boards when you need `TransformFromCopy`, branding morphs, or plugin mobjects that are not registered diagrams.

## Themes

Do not hardcode colors. Resolve through `get_theme()` / `set_theme` / `use_theme`. Cards, badges, and STEM visualizers already read the palette.

## Scene hygiene

- One `show_slide` per `Slide`; use `pause_slide` for a beat after lecture cues finish.
- `lecture=True` hides cueable body then reveals it — skip it (`lecture=False`) when you want the full slide visible immediately.
- Keep `lecture_gap` in the 0.35–0.55s range when voiceover is off so reveals do not slam together.
- Prefer `VoiceoverSlideScene` even without TTS: the same cue path runs on timed waits.

## Next

- [Voiceover](03-voiceover.md)
- [Visualizations](04-visualizations.md)

# Merging visualizations

Slides can host named diagrams, reserved animation regions, existing Manim `VGroup`s, and Cueable visualizers from other AOS plugins. Matplotlib/Plotly are **not** first-class: convert them to Manim mobjects first, then use one of the four patterns below.

## 1. Named diagram registry

Factories have signature `(width, height, theme, **kwargs) -> VGroup`. Built-ins (lazy-import sibling packages; placeholder text if the import fails):

| Name | Backend | Typical kwargs |
|---|---|---|
| `gradient_descent` | `aos_manim_maths.DerivativeVisualizer` | `f` / `expr`, `x` / `x0` |
| `newton_method` | `aos_manim_maths.RootFindingVisualizer` | `f` / `expr`, `x0` |
| `binary_search` | `aos_manim_algorithms.BinarySearchVisualizer` | `arr` / `array`, `target` |

Markdown:

````markdown
---
layout: two-column
title: Gradient Descent
---

```diagram
gradient_descent(f=x**2, x=1.5)
```
````

Colon fence:

```markdown
:::diagram
newton_method(f=x**2-2, x0=1.5)
:::
```

Python:

```python
from aos_manim_slides import DiagramRef, Slide, SlideSpec

slide = Slide.from_spec(SlideSpec(
    title="Gradient Descent",
    layout="diagram-focus",
    blocks=[DiagramRef("gradient_descent", kwargs={"f": "x**2", "x": 1.5})],
))
```

Register your own (call this before `from_spec` / `deck_from_markdown`):

```python
from manim import VGroup
from aos_manim_slides import register_diagram

def my_plot(width, height, theme, **kwargs):
    # Build a VGroup sized to width × height; use theme.text_main / theme.primary.
    return group

register_diagram("my_plot", my_plot)
```

`build_diagram(name, width, height, theme=None, **kwargs)` raises `DiagramNotFoundError` for unknown names (unlike animation slots).

## 2. Animation slots

Reserve a diagram-sized cell. Register a factory when the sim exists. Unknown names still layout as a labeled rounded frame so Markdown parses early. Auto-scripts emit `CueAction.PLAY` on the slot id (`anim0`).

````markdown
---
layout: diagram-focus
title: The Lorenz attractor
---

```animation
lorenz(sigma=10, rho=28, beta=2.667)
```
````

```python
from aos_manim_slides import AnimationSlot, Slide, SlideSpec, register_animation

def build_lorenz(width, height, theme, **kwargs):
    group = VGroup(...)  # Cueable: play_on, apply_cue, cue_targets, step_count
    def play_on(scene):
        ...
    def apply_cue(scene, cue):
        ...
    def cue_targets():
        return {"self": group}
    def step_count():
        return 0
    group.play_on = play_on
    group.apply_cue = apply_cue
    group.cue_targets = cue_targets
    group.step_count = step_count
    return group

register_animation("lorenz", build_lorenz)

slide = Slide.from_spec(SlideSpec(
    title="Lorenz",
    layout="diagram-focus",
    blocks=[AnimationSlot(name="lorenz", kwargs={"sigma": 10, "rho": 28})],
))
```

`register_animation` / `build_animation` live next to the diagram registry. Prefer this over embedding a long integrator inside `SlideSpec`.

## 3. Raw Manim mobjects

`TwoColumnSlide` wraps existing groups as `RawMobject` (not exported from the package root):

```python
from manim import VGroup, MathTex
from aos_manim_slides import TwoColumnSlide
from aos_manim_slides.document import RawMobject
from aos_manim_slides import Slide, SlideSpec, Paragraph

left = VGroup(MathTex(r"f(x)=x^2"))
right = some_visualizer_vgroup

slide = TwoColumnSlide("Compare", left, right)

# Or explicit spec:
slide = Slide.from_spec(SlideSpec(
    title="Compare",
    layout="two-column",
    left=[Paragraph("We minimize"), RawMobject(mobject=left)],
    right=[RawMobject(mobject=right)],
))
```

`slide.add_content(extra_mobject)` appends to the content group **after** spec layout (manual placement). Prefer `RawMobject` in the spec so overflow and packing still apply.

## 4. Cueable contract

Used by `CueResolver` for `STEP` / `PLAY` and by `append_step_cues` (`{id}s{i}` marks). Protocol (`aos_manim_core.Cueable`):

```python
def cue_targets(self) -> dict:   # {"curve": mob, "point": mob, ...}
    ...

def apply_cue(self, scene, cue) -> None:
    # cue.action, cue.payload.get("i") for steps
    ...

def step_count(self) -> int:
    ...
```

Optional `play_on(scene)` is used when `PLAY` has no `apply_cue`. Nested targets appear in the slide cue index as `d0.curve`.

Example: `RootFindingVisualizer.build_cueable_root_finding(...)` in `examples/ecosystem_lecture.py` — reveal the curve, then `apply_cue(..., CueAction.STEP, payload={"i": k})` on each bookmark.

## Choosing a pattern

| You have | Use |
|---|---|
| A named, reusable plot | `register_diagram` + `` ```diagram `` |
| A sim not ready yet / PLAY cue | `AnimationSlot` + `register_animation` |
| An already-built `VGroup` | `RawMobject` / `TwoColumnSlide` |
| Hand-timed copy-to-diagram | `CopyExplain` (see [05-components-and-plugins.md](05-components-and-plugins.md)) |

## Next

- [Components and plugins](05-components-and-plugins.md)

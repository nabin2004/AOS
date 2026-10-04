# MotionGram ManimDSL schema

This document is the LLM-facing contract for the ManimCE-targeting
`motiongram.manimgram` package. It covers ManimDSL only. It does not describe
the native MotionGram scene manifest, scientific DSL, slide DSL, or Skia
renderer.

## Purpose and output rules

An LLM should emit one YAML mapping or equivalent JSON object that validates as
`ManimGramScene`. It should emit the DSL, never Python or Markdown.

The runtime path is:

`YAML/JSON -> Pydantic validation -> deterministic ManimCE Python -> render`

The authoritative machine-readable schema is generated from the installed
models:

```bash
motiongram manimgram schema -o manimgram_schema.json
```

For application code, use the context helpers rather than copying this page:

```python
from motiongram.manimgram import get_llm_context, get_llm_context_payload

text_context = get_llm_context()
structured_context = get_llm_context_payload()
```

`structured_context` contains `system_prompt`, `json_schema`, and verified
`few_shot_examples`. `text_context` combines the same information into one
system/developer-message-ready string.

## Root document

```yaml
scene: {}       # optional; defaults to a Scene
camera: {}      # optional
mobjects: []    # visual entities
timeline: []    # actions and optional voiceover blocks
```

Unknown fields are rejected at the root and in all structural objects. The
`mobjects[*].props` and `timeline[*].params` mappings remain open because they
are passed through as Manim constructor/command arguments.

## Scene and rendering configuration

```yaml
scene:
  class_name: GeneratedScene
  type: Scene                 # Scene | MovingCameraScene | ThreeDScene | VoiceoverScene
  background_color: "#1C1C1C"
  config:
    pixel_width: 1920
    pixel_height: 1080
    frame_rate: 30
    voice: alba
    backend: auto
    model: null
    cache_dir: voiceover_cache
    speech_service: AOSSpeechService
  voiceover:                  # optional override for narrated scenes
    voice: alba
    backend: auto
    model: null
    cache_dir: voiceover_cache
    speech_service: AOSSpeechService
```

`VoiceoverScene` is required when using narration. A timeline item of
`type: voiceover_block` also enables voiceover compilation.

## Mobjects

Each mobject requires a unique identifier and a Manim class name. IDs must be
valid Python identifiers because the compiler uses them as generated variable
names.

```yaml
mobjects:
  - id: title
    type: Text
    props:
      text: "A title"
      font_size: 44
      color: YELLOW
    layout:
      to_edge: {edge: UP, buff: 0.5}
    state:
      visible: true
      opacity: 1.0
      scale: 1.0
```

Common supported classes include `Text`, `MathTex`, `Tex`, `Matrix`,
`IntegerMatrix`, `DecimalMatrix`, `MobjectMatrix`, `Circle`, `Square`,
`Rectangle`, `Line`, `Arrow`, `Dot`, `Polygon`, `Arc`, `Sector`, `Axes`,
`ThreeDAxes`, `Surface`, `DecimalNumber`, `Sphere`, `Cube`, `Cylinder`, and
any compatible Manim class accepted by the compiler.

Important `props` conventions:

- `MathTex`/`Tex`: use `tex`, `text`, or `expression`.
- `Matrix` family: use `matrix`; `bracket_color` is converted to Manim's
  bracket configuration.
- `Axes`/`ThreeDAxes`: use `x_range`, `y_range`, and `z_range` where relevant.
- Colors may be Manim constants such as `YELLOW` or hex strings such as
  `"#FFD54F"`.

## Layout

`layout` operations are applied in this order: scale, center or move-to,
next-to, edge/corner, align-to, then shift.

```yaml
layout:
  center: true
  move_to: [0, 1, 0]
  next_to:
    target: title
    direction: DOWN       # UP | DOWN | LEFT | RIGHT | UL | UR | DL | DR | IN | OUT
    buff: 0.5
    aligned_edge: LEFT   # optional: UP | DOWN | LEFT | RIGHT
  to_edge: {edge: UP, buff: 0.5}
  to_corner: {corner: UR, buff: 0.5}
  align_to: {target: title, direction: LEFT}
  shift: [0, -1, 0]
  scale: 0.8
```

Use IDs in layout references, not generated Python variables or array indices.

## Timeline actions

Every action has an `action` name. `run_time` is in seconds and accepts a
number or a string such as `"1.5s"`. `rate_func` is passed to Manim as a
Python expression and should normally be a known Manim easing name.

| Action | Required fields | Purpose |
|---|---|---|
| `Create`, `Write`, `Unwrite`, `FadeIn`, `FadeOut` | `target` | Show or hide a mobject |
| `Circumscribe`, `Indicate`, `Wiggle`, `Flash` | `target` | Emphasis animation |
| `Transform`, `ReplacementTransform`, `TransformMatchingTex`, `TransformMatchingShapes` | `source`, `target` | Transform one mobject into another |
| `RoutedTransform` | `source`, `target`, `routes` | Transform selected submobjects |
| `Wait` | optional `duration` | Pause; otherwise uses `run_time` |
| `WaitUntilBookmark` | `mark` | Wait for a voiceover bookmark |
| `Orbit`, `Focus`, `Pan`, `Zoom`, `ResetView`, `CameraAction` | camera fields/`params` | Camera choreography |

Examples:

```yaml
timeline:
  - action: Write
    target: title
    run_time: 1.0
  - action: TransformMatchingTex
    source: equation_before
    target: equation_after
    run_time: 1.5
    rate_func: smooth
  - action: Wait
    duration: 0.5
```

Timeline references are validated against the mobject IDs. `RoutedTransform`
requires at least one route, and transform actions require `source` and
`target`.

## Semantic selectors and routed transforms

Selectors avoid fragile guessed Manim submobject indices:

| Mobject family | Selectors |
|---|---|
| Matrix | `entry[row,col]`, `row[index]`, `col[index]`, `brackets`, `bracket.left`, `bracket.right` |
| MathTex/Tex | `term[text]`, `part[index]` |
| Axes | `x_axis`, `y_axis`, `z_axis`, `point[x,y]`, `c2p[x,y]` |
| Table | `cell[row,col]`, `row[index]`, `col[index]` |

```yaml
- action: RoutedTransform
  source: matrix_a
  target: matrix_b
  run_time: 2.0
  fallback: by_index       # by_index | fade | none
  routes:
    - from: "entry[0,0]"
      to: "entry[0,0]"
      animation: ReplacementTransform
    - from: "brackets"
      to: "brackets"
      animation: Transform
```

## Voiceover blocks

```yaml
timeline:
  - type: voiceover_block
    text: "First show A. <bookmark mark='SHOW_A'/> Now transform it."
    actions:
      - action: WaitUntilBookmark
        mark: SHOW_A
      - action: Create
        target: matrix_a
        run_time: 1.2
```

Bookmarks are embedded in `text`; the matching `WaitUntilBookmark` action
controls when the visual action occurs.

## LLM integration checklist

1. Give the model `get_system_prompt()` or `get_llm_context()`.
2. Use `get_json_schema()` as the provider's structured-output schema.
3. Require YAML/JSON only, with no prose or code fences.
4. Validate with `ManimGramScene.model_validate(...)` before compilation.
5. Compile with `compile_dsl(...)`; only then render with the ManimGram CLI.

```python
from motiongram.manimgram import get_json_schema
from motiongram.manimgram.compiler import compile_dsl
from motiongram.manimgram.schema import ManimGramScene

data = model_output_as_dict  # provider constrained by get_json_schema()
spec = ManimGramScene.model_validate(data)
python_source = compile_dsl(spec)
```

This schema validates structure and references; it does not prove that every
arbitrary Manim constructor property in `props` is supported by the installed
Manim version.

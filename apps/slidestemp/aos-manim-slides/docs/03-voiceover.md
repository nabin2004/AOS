# Voiceover and lecture cues

`aos-manim-slides` does **not** implement TTS. It orchestrates [manim-voiceover](https://github.com/ManimCommunity/manim-voiceover) bookmarks: spoken text contains `<bookmark mark='…'/>` tags; visuals reveal, highlight, or step when those marks fire.

Without the extra, the same cues still run on timed gaps (`lecture_gap`, default `0.35` seconds). Audio formats, API keys, and cache directories belong to the speech service you pass in, not to this plugin.

## Install and enable

```bash
pip install -e "aos-manim-slides[voiceover]"
```

That extra is `manim-voiceover>=0.3.0`. Then attach a speech service **before** `show_slide` / `beats`:

```python
from manim_voiceover.services.gtts import GTTSService
from aos_manim_slides import VoiceoverSlideScene, Slide

class LecturedDeck(VoiceoverSlideScene):
    def construct(self):
        self.enable_voiceover(GTTSService())
        for slide in Slide.deck_from_markdown(markdown):
            self.show_slide(slide, lecture=True)
```

`enable_voiceover(speech_service)` calls `set_speech_service` when the mix-in is present and sets `aos_voiceover_enabled`. If the import fails or you pass `None`, it returns `False` and cues use `scene.wait(gap)` instead.

Other manim-voiceover services (Azure, Recorder, Coqui, …) work the same way: construct the service, pass it to `enable_voiceover`. Keys and output formats are documented by that library.

## Pipeline

```text
Markdown / SlideSpec
        │
        ▼
assign_content_ids   (li0, p0, eq0, anim0, d0, …)
        │
        ▼
script_for_slide  →  NarrationScript  (text + Cue list)
        │
        ▼
VoiceoverSlideScene.show_slide(..., lecture=True)
        │
        ├─ hide_lecture_body   (opacity 0 on cue targets)
        ├─ CueResolver(targets, cueables, theme)
        └─ play_script(scene, script, resolver, gap=lecture_gap)
                │
                ├─ voiceover on:  with scene.voiceover(text=…): wait_until_bookmark(mark)
                └─ voiceover off: scene.wait(gap) then apply cue
```

`SlideScene` uses `lecture=False` unless you pass `True`. `VoiceoverSlideScene` defaults `lecture=True`.

## Bookmark syntax and ids

```text
<bookmark mark='li0'/>Reveal the first idea.
```

Quotes may be single or double. Marks must match cue targets.

| Prefix | Source |
|---|---|
| `p0`, `p1`, … | Paragraphs |
| `h0`, … | Headings (`##`+) |
| `eq0`, … | Equations |
| `li0`, … | List items (also `l0` for the list block) |
| `c0`, … | Callouts |
| `code0`, … | Code fences |
| `d0`, … | Diagram refs |
| `anim0`, … | Animation slots |
| `img0`, … | Images |
| `d0s0`, `d0s1`, … | Cueable **steps** (`STEP`, payload `{"i": n}`) |

Child cue targets on a Cueable are indexed as `d0.curve`, `d0.point`, … when `cue_targets()` returns those keys.

## Auto-script vs authored vs explicit cues

`script_for_slide(spec, cueables)` chooses:

1. **`spec.cues` set** — use those `Cue` objects; spoken text is `spec.voiceover` (may be empty). Bookmarks are injected if missing.
2. **`spec.voiceover` set** — bind authored marks onto auto-generated cues (`bind_authored_script`). Marks that match auto `mark` or `target_id` reuse that cue; leftover marks map onto unused auto cues in order.
3. **Neither** — `auto_script_from_spec`: one spoken fragment per block, plus `Step N.` for each Cueable step.

Spoken fragments for auto-script (you can override with `voiceover: |`):

| Block | Spoken |
|---|---|
| Paragraph / heading | The text itself |
| Equation | `"the equation"` |
| List item | The item text |
| Callout | `"{title}. {body}"` |
| Code | `"this code"` |
| Diagram | `"watch the {name} diagram"` |
| Animation | `"watch the {name} animation"` (`PLAY`) |
| Image | Caption or `"this figure"` |

Markdown example with authored bookmarks (from `examples/slides/calculus_methods.md`):

```markdown
---
layout: diagram-focus
title: Newton on x^2 - 2
voiceover: |
  Watch Newton on x squared minus two.
  <bookmark mark='d0'/>Start from the curve and the initial guess.
  <bookmark mark='d0s0'/>Each tangent hits the axis at the next iterate.
---
```

Python:

```python
from aos_manim_core import Cue, CueAction
from aos_manim_slides import SlideSpec, Equation

spec = SlideSpec(
    title="Newton",
    layout="equation-focus",
    blocks=[Equation(r"x_{n+1}=x_n-f(x_n)/f'(x_n)")],
    voiceover="The update. <bookmark mark='eq0'/>Newton's step.",
)
```

## Cue actions

From `aos_manim_core.CueAction`:

| Action | Visual |
|---|---|
| `REVEAL` | `FadeIn` (or opacity 1) |
| `HIGHLIGHT` | `SurroundingRectangle` in theme `highlight_a` |
| `INDICATE` | `Indicate` |
| `DIM` | Opacity (payload `opacity`, default 0.35) |
| `STEP` | `obj.apply_cue(scene, cue)` with `payload["i"]` |
| `PLAY` | `apply_cue` or `play_on` |
| `SFX` | `scene.add_sound(payload["name"])` if present |

Lecture boards expose the same id contract:

```python
from aos_manim_slides import BulletBoard

board = BulletBoard("Agenda", ["Define the field", "Show the flow"])
board.cue_targets()       # {"li0": …, "li1": …}
board.voiceover_script()  # bookmarked speech for later automation
```

## `beats()` (hand-timed lecture)

When you are not using `Slide` / `show_slide`, drive marks yourself:

```python
self.lecture_gap = 0.5
self.beats(
    "Start with a derivative. "
    "<bookmark mark='D0'/>The title. "
    "<bookmark mark='D1'/>A smooth curve.",
    [
        ("D0", lambda: panel.play_title(self)),
        ("D1", lambda: panel.play_item(self, 0)),
    ],
)
```

If a mark is missing from `text`, `beats` appends `<bookmark mark='…'/>`. With voiceover enabled it uses `wait_until_bookmark`; otherwise it runs the callback then `wait(lecture_gap)` (note: `beats` reads `lecture_gap` with a 0.55 fallback if unset).

Full tour: `examples/ecosystem_lecture.py`. Bookmark-only list slide: `examples/lecture_cues.py`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Everything appears at once | `lecture=False`, or `show_slide` on `SlideScene` without `lecture=True` |
| Cues fire but no speech | Extra not installed, `enable_voiceover` not called / returned `False` |
| Speech but no reveals | Bookmark `mark` does not match assigned ids (`eq0` vs `eq1`); authored marks unbound |
| Steps skipped | Visualizer `step_count()` is 0 or not Cueable; step marks `d0s0` missing from authored script |
| Waits feel slow/fast | Tune `self.lecture_gap`; VO timing follows the TTS audio, not the gap |
| `wait_until_bookmark` errors | Service/cache issue in manim-voiceover; try Recorder or disable VO to isolate visuals |

## Next

- [Visualizations](04-visualizations.md) (Cueable factories, `PLAY` slots)
- [Components and plugins](05-components-and-plugins.md) (`CopyExplain` + `beats`)

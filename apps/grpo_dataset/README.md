# ManiBench GRPO Dataset Schemas

## Repository Layout (Implemented)

The repository is now organized around per-problem bundles under `data/problems/<MB-ID>/`.

```text
manibench-grpo/
├── data/
│   ├── problems/
│   │   └── MB-001/
│   │       ├── problem.json
│   │       ├── reference.py
│   │       ├── visual_events.json
│   │       ├── coverage.json
│   │       ├── version_notes.json
│   │       └── ref_embeddings.npy
│   ├── splits/
│   │   ├── train.jsonl
│   │   ├── val.jsonl
│   │   └── test.jsonl
│   └── metadata.json
├── reward_model/
│   ├── executability.py
│   ├── vcer.py
│   ├── alignment.py
│   ├── clip_reward.py
│   ├── coverage.py
│   ├── narration.py
│   └── aggregate.py
├── scripts/
│   ├── render_sandbox.py
│   ├── extract_and_embed_frames.py
│   ├── build_dataset.py
│   ├── validate_dataset.py
│   └── test_narration_reward.py
├── configs/
│   └── reward_weights.yaml
└── rollouts/
```

Notes:
- `rollouts/` is transient GRPO output and should not be versioned.
- Raw `.mp4`/frame assets are intentionally excluded from dataset artifacts.
- `ref_embeddings.npy` is the portable reference artifact for clip alignment.

## Bootstrapping Commands

```bash
python scripts/build_dataset.py --data-root data --seed 20260817
python scripts/validate_dataset.py --data-root data
```

## `data/problems/MB-XXX/problem.json`

Single source of truth per problem — merges the prompt, Appendix A.1 metadata, and pointers to sibling files. `build_dataset.py` reads this to emit `train.jsonl` rows.

```json
{
  "id": "MB-002",
  "title": "Gradient Descent",
  "youtube_video_id": "IHZwWFHWa-w",
  "video_timestamp_range": [142.0, 210.5],
  "category": ["drift-sensitive", "direct-visualization"],
  "difficulty_level": 3,
  "domain": ["ML", "Calculus"],

  "full_prompt": "Animate a single-variable gradient descent process on a loss curve L(w) = (w-2)^2 + 1. Show the parameter w updating step by step, with a dot moving along the curve toward the minimum, and the tangent line / gradient arrow visualized at each step before the dot moves.",

  "raw_code_status": "collected",
  "raw_code_path": "reference_source_gl/gradient_descent.py",

  "reference_code_analysis": {
    "framework": "manim_gl",
    "total_lines": 8598,
    "scene_classes": [
      {"name": "GradientDescentWrapper", "key_methods": ["construct", "show_step"]}
    ],
    "visual_techniques": ["ValueTracker-driven dot motion", "TangentLine", "always_redraw updater"],
    "manim_api_patterns": {
      "updaters": ["always_redraw", "f_always"],
      "animation_types": ["MoveAlongPath", "Transform"],
      "custom_classes": ["GradientArrow"]
    }
  },

  "required_visual_events_path": "visual_events.json",
  "coverage_requirements_path": "coverage.json",
  "version_conflict_notes_path": "version_notes.json",
  "reference_embeddings_path": "ref_embeddings.npy",

  "success_criteria": {
    "min_executability": 1.0,
    "min_alignment": 0.7,
    "min_coverage": 0.5,
    "max_vcer": 0.0
  },

  "common_failure_modes": [
    {"pattern": "loss_curve.animate before dot.animate.move_to", "severity": "high", "note": "inverts causal order — see Listing 2 in paper"}
  ]
}
```

Notes:
- `video_timestamp_range` is new vs. your draft — it's what `extract_and_embed_frames.py` uses to pull only the relevant clip instead of the whole video, and it's what lets you discard raw frames after embedding (see reasoning in prior message on why raw video shouldn't ship in the dataset).
- `reference_code_analysis` stays nested here rather than a separate file since it's read-only ground truth, written once, never touched by the reward pipeline at train time.

---

## `data/problems/MB-XXX/visual_events.json`

This is the file `alignment.py` **and** `clip_reward.py` both consume — one list, two consumers, so timing and text descriptions never drift out of sync between your keyword heuristic and your CLIP heuristic.

```json
{
  "problem_id": "MB-002",
  "events": [
    {
      "event_id": "ev_01",
      "description": "A dot sits on the loss curve at the initial parameter value",
      "weight": 0.15,
      "critical": true,
      "expected_time_range": [0.0, 3.0],
      "keyword_bank": ["Dot(", "loss_curve", "point_from_proportion"],
      "clip_query": "a small dot resting on a smooth blue parabola curve"
    },
    {
      "event_id": "ev_02",
      "description": "A tangent line or gradient arrow appears at the dot's current position before it moves",
      "weight": 0.30,
      "critical": true,
      "expected_time_range": [3.0, 6.0],
      "keyword_bank": ["TangentLine", "gradient", "Arrow", "always_redraw"],
      "clip_query": "an arrow or tangent line touching a point on a curve, indicating slope"
    },
    {
      "event_id": "ev_03",
      "description": "The dot moves along the curve toward the minimum, updating its x-position",
      "weight": 0.35,
      "critical": true,
      "expected_time_range": [6.0, 10.0],
      "keyword_bank": ["ValueTracker", ".animate.move_to", "MoveAlongPath"],
      "clip_query": "a dot sliding down a curve toward its lowest point"
    },
    {
      "event_id": "ev_04",
      "description": "A numeric readout of the current loss value updates as the dot moves",
      "weight": 0.20,
      "critical": false,
      "expected_time_range": [6.0, 10.0],
      "keyword_bank": ["DecimalNumber", "always_redraw"],
      "clip_query": "a decimal number label changing next to a graph"
    }
  ]
}
```

Field notes:
- `expected_time_range` is in **rendered-video seconds relative to scene start** — same clock `alignment.py` uses for `t_i` and `clip_reward.py` uses to sample frame windows from the model's own render (not the reference).
- `keyword_bank` replaces the old single global keyword list — scoping it per-event is what fixes the "Llama-3.1-8B gets 1.0 alignment despite 8.3% executability" saturation problem you flagged in §9.6.
- `clip_query` is deliberately a short natural-language phrase, not the full `description` — CLIP text encoders degrade on long/compound sentences, so keep this to one concrete visual scene per event.
- `weight` still sums to 1.0 per problem, feeding straight into your Eq. (3) Alignment formula unchanged.

---

## CLIP reward — how it consumes both files

```python
# reward_model/clip_reward.py (sketch)
def clip_alignment_score(rendered_video_path, visual_events, fps_sample=2):
    frames = extract_frames(rendered_video_path, fps_sample)  # list[(t, frame)]
    total, denom = 0.0, 0.0
    for ev in visual_events["events"]:
        t0, t1 = ev["expected_time_range"]
        window = [f for t, f in frames if t0 <= t <= t1]
        if not window:
            score = 0.0  # event window never occurred -> penalize like p_i=0
        else:
            sims = [clip_similarity(ev["clip_query"], f) for f in window]
            score = max(sims)  # best matching frame in the expected window
        total += ev["weight"] * score
        denom += ev["weight"]
    return total / denom
```

Combine this with `alignment.py`'s keyword-based score (e.g. `0.5 * keyword_align + 0.5 * clip_align`) in `aggregate.py` so a bad keyword match can still get partial credit from CLIP, and vice versa — that blended score is what goes into the GRPO reward alongside `executability` and `vcer` as hard gates (zero out reward if executability fails, regardless of alignment).

---

## Narration Reward (`reward_model/narration.py`)

For multi-modal tasks using **Manim Voiceover**, code generations are also scored for proper voiceover and synchronization structure:
- **`VoiceoverScene` Inheritance (0.25)**: Ensures the class derives from `VoiceoverScene`.
- **Speech Service Setup (0.20)**: Checks for `self.set_speech_service(...)`.
- **Voiceover Blocks (0.25)**: Evaluates use of `with self.voiceover(...)` blocks.
- **SSML Bookmarks (0.15)**: Checks for precise narration timestamps via `<bookmark mark="..." />`.
- **Bookmark Synchronization (0.15)**: Evaluates synchronization with `self.wait_until_bookmark(...)`.

Run validation:
```bash
python scripts/test_narration_reward.py
```

---

## `coverage.json` and `version_notes.json`

Keep these as previously scoped — no changes needed:

```json
// coverage.json
{
  "problem_id": "MB-002",
  "requirements": {
    "Math":       {"weight": 0.35, "expected": ["MathTex", "loss function label", "gradient symbol"]},
    "Visual":     {"weight": 0.30, "expected": ["set_color on active point", "arrow indicator"]},
    "Numeric":    {"weight": 0.20, "expected": ["DecimalNumber", "ValueTracker"]},
    "Structural": {"weight": 0.15, "expected": ["VGroup", "wait() pacing between steps"]}
  }
}
```

```json
// version_notes.json
{
  "problem_id": "MB-002",
  "conflicts": [
    {"category": "Animation renames", "gl_construct": "ShowCreation", "ce_equivalent": "Create", "severity": "auto-fail if used"},
    {"category": "Class configuration", "gl_construct": "CONFIG dict", "ce_equivalent": "__init__ parameters", "severity": "auto-fail if used"}
  ]
}
```

---

## `data/splits/train.jsonl` row (what GRPO actually loads)

```json
{"id": "MB-002", "prompt": "Animate a single-variable gradient descent...", "problem_path": "data/problems/MB-002/problem.json"}
```

Keep the JSONL row minimal — GRPO training loop loads the prompt for generation, then `aggregate.py` pulls the rest from `problem_path` only when scoring a completion. This keeps `train.jsonl` diffable and light even at 150+ problems.
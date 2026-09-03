# ManiBench Data Annotation Guide
### Turning 3b1b/videos source into GRPO problem bundles

Companion to `manibench_grpo_schemas.md` (field-level schema reference). This doc is the annotator-facing *process*: how to go from a 3Blue1Brown video to a complete, validated problem folder under `data/problems/MB-XXX/`.

## Repository policies

- Dataset artifacts live under `data/`.
- Reward logic lives under `reward_model/`.
- Utility tooling lives under `scripts/`.
- Transient generation artifacts live under `rollouts/` and must not be committed.
- Raw video clips and extracted frames must not be committed; keep only `ref_embeddings.npy` in each problem folder.

---

## 0. TL;DR workflow

1. Pick a video/concept → assign an `MB-XXX` ID
2. Find the source folder in `3b1b/videos`
3. Determine scene order (code → published video)
4. Watch + rough-timestamp the segment
5. Extract `reference_code_analysis` from the code
6. Write `full_prompt` (no solution leakage)
7. Build `visual_events.json` (weights, timing, keyword_bank, clip_query)
8. Fill `coverage.json`
9. Fill `version_notes.json` (GL→CE conflicts)
10. Pull reference clip → CLIP-embed → discard frames → validate → register in `metadata.json`

---

## 1. Source repos & licensing — read this before annotating anything

You're pulling from **three separate repos with three separate licenses**. Mixing them up is the easiest way to create a legal headache once this dataset is public on HuggingFace.

| Repo | Contents | License |
|---|---|---|
| [`3b1b/manim`](https://github.com/3b1b/manim) | ManimGL engine itself | MIT |
| [`3b1b/videos`](https://github.com/3b1b/videos) | Per-video scene code (what you're annotating from) | **CC BY-NC-SA 4.0** |
| [`ManimCommunity/manim`](https://github.com/ManimCommunity/manim) | Manim CE (what generated code targets) | MIT (double-licensed, 3blue1brown LLC + Community Developers) |
| [`3b1b/captions`](https://github.com/3b1b/captions) | Transcripts/timing data (optional, see §4.3) | Not explicitly stated — treat as NC until confirmed |
| YouTube video itself | Pixels/audio | Standard copyright, all rights reserved by default — **not** covered by any of the above |

The engine is MIT, but the video-specific scene code you're actually reading and annotating from — the thing that lives in `_2015/` through `_2026/` — is under the <cite index="13-1">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</cite>, not MIT. That's Attribution + NonCommercial + ShareAlike. Practical implications for this dataset:

- **Attribution**: `metadata.json` and any dataset card must credit 3Blue1Brown / Grant Sanderson as the source of reference code and video content.
- **NonCommercial**: don't ship or license this dataset for commercial use. If it ends up powering a commercial product later, that specific dependency needs to be revisited.
- **ShareAlike**: if `reference.py` in a problem bundle is a lightly-cleaned copy/port of GL source (see §4.4), that field inherits CC BY-NC-SA obligations even if the rest of your annotations (prompts, event lists, weights — your own original writing) are licensed more permissively.
- **Never redistribute video frames or clips.** This is true regardless of the code license — YouTube video rights are separate and unaddressed by CC BY-NC-SA. Pull frames locally, embed with CLIP, discard the pixels. Only `ref_embeddings.npy` (a non-reversible derived artifact) goes in the dataset. This was already the design from the schema doc — the license research just confirms it's not optional.

---

## 2. Environment setup

```bash
# Reference repos
git clone https://github.com/3b1b/manim.git manimgl-src
git clone https://github.com/3b1b/videos.git 3b1b-videos
git clone https://github.com/ManimCommunity/manim.git manimce-src   # for optionally test-rendering CE ports
git clone https://github.com/3b1b/captions.git 3b1b-captions        # optional, transcript timing shortcut

# Annotation tooling (separate venv from either manim install — dependency conflicts are common)
python -m venv .venv-annot && source .venv-annot/bin/activate
pip install yt-dlp open_clip_torch torch --break-system-packages
sudo apt install ffmpeg
```

Keep ManimGL and ManimCE in **separate virtualenvs** if you plan to test-render anything — they conflict on transitive dependencies (moderngl/pycairo versions in particular) even though the package names differ.

---

## 3. Per-problem workflow

### Step 1 — Pick the problem, find the source folder

`3b1b/videos` is organized by year, then a topic slug: <cite index="13-1">_2015 through _2026, plus custom, once_useful_constructs, outside_videos, and sublime_custom_commands</cite> at the top level. Folder names are usually descriptive topic abbreviations (the README's own example is `_2023/optics_puzzles`). Once you've picked a video by title/topic, grep for it rather than guessing the exact folder:

```bash
grep -rl "class.*GradientDescent" 3b1b-videos/_20*/
# or, if class names don't match your intuition, search by concept keyword:
grep -rli "eigen\|bayes\|windmill\|hairy.ball" 3b1b-videos/_20*/ 
```

Grant's filenames and class names are almost always descriptive, so keyword grep across `.py` files under the year folders is the fastest path when you don't already know the exact file.

### Step 2 — Determine scene order (code → published video)

Check whether the target module defines a module-level `SCENES_IN_ORDER` list. This is exactly what 3b1b's own build tooling (`stage_scenes.py`) uses to assemble a rough cut — <cite index="14-1">it reads SCENES_IN_ORDER if present, and otherwise falls back to deducing scene order from the order classes are defined in the file</cite>. So:

- **If `SCENES_IN_ORDER` exists** → that list is your authoritative scene sequence for the video.
- **If it doesn't** → default to source-definition order (top to bottom in the file) as your best guess.
- **Caveat**: the final YouTube edit can still reorder, cut, or splice in narration-only footage with no corresponding `Scene` class. Treat this as a strong prior, not ground truth — always confirm by watching (Step 3).

`stage_scenes.py` itself won't run for you out of the box — it's hardcoded to Grant's personal Dropbox path for pre-rendered clips — but the `SCENES_IN_ORDER` convention it relies on is the transferable, useful part.

### Step 3 — Watch and rough-timestamp

- Open the YouTube video. Check the description for chapter markers — many 3b1b videos have them and make good coarse anchors.
- Optionally check `3b1b-captions/` for a timed transcript of the target video. That repo was originally built from Whisper transcription with timing, though Grant has since moved primary translation workflow to a separate tool (criblate.com) — <cite index="15-1">the repo's stated purpose shifted from active translation tracking</cite>, so treat any transcript files you find there as a possible shortcut, not a guaranteed-present resource. Narration timing is a solid proxy for visual event timing, since Grant typically narrates an action as it happens.
- Scrub to the segment matching your source file/scene. Note start/end in **video-absolute time** first, then convert to **scene-relative time** (subtract segment start) — that relative clock is what `video_timestamp_range` and every `expected_time_range` in `visual_events.json` use.

### Step 4 — Read the code, extract `reference_code_analysis`

- Identify the `Scene` subclass(es) and their key methods.
- Grep for the animation calls and mobject types actually used — this feeds `visual_techniques` / `manim_api_patterns` in `problem.json`:
  ```bash
  grep -nE "ShowCreation|Transform|always_redraw|ValueTracker|MoveAlongPath" your_file.py
  ```
- Note any custom mobjects/helpers pulled from `manim_imports_ext` or `once_useful_constructs/` — anything not in vanilla ManimGL/CE. These almost always become `custom_mobjects` entries in `version_notes.json`, since CE has no direct equivalent.
- **Optional stretch step**: hand-port a cleaned, CE-compatible version of the reference scene into `reference.py`. This isn't required for the reward pipeline to work (it scores generated code against `visual_events.json`, not against a reference implementation), but it's useful for sanity-checking that your event list is achievable at all. Skip it if time-constrained — 12 problems is fine to do by hand, 150+ probably isn't.

### Step 5 — Write `full_prompt`

Describe the *what*, not the *how*. State the concept and the expected visual outcome in plain language — never name `Scene` subclasses, method names, or specific Manim API calls. That's solution leakage: a model could pattern-match prompt vocabulary directly to your `keyword_bank` terms and score well without actually solving the visual-logic problem.

Calibrate specificity to your target difficulty — reuse the existing pilot set as your anchor points for consistency:

| Level | Characteristics | Pilot examples |
|---|---|---|
| 2 | Single concept, one or two moving parts | Determinant, Medical Test (Bayes) |
| 3 | Multi-step process, clear causal chain | Gradient Descent, CLT, Chain Rule |
| 4 | Multiple interacting representations or abstract structure | Eigenvectors, Taylor Series, Windmill |
| 5 | Non-obvious visualization strategy required | Hairy Ball Theorem |

Lower difficulty can be more explicit about what to show; higher difficulty should state the mathematical goal and leave the visualization strategy to the model.

### Step 6 — Build `visual_events.json`

- Chunk the scene into 3–6 discrete visual beats (the pilot Gradient Descent example in the schema doc used 4).
- Per event: `weight` (sum to 1.0 per problem — weight causal/structural beats higher than decorative ones), `critical` (true if its absence alone should tank the score), `expected_time_range` (scene-relative), `keyword_bank` (3–5 grep-able terms), `clip_query` (one concrete visual phrase, not a compound sentence).
- **Write `keyword_bank` in CE vocabulary, not GL vocabulary.** Your reference source is GL (`ShowCreation`, `CONFIG` dicts, etc.), but the code you're actually grading is CE-generated. A keyword bank full of GL-only terms will never match anything a model produces. Cross-reference against the CE equivalents when in doubt.
- **Leakage check**: could a model satisfy every `keyword_bank` entry with generic boilerplate and still miss the point of the animation? If yes, add or reweight events until keyword presence and actual correctness are harder to decouple.

### Step 7 — Fill `coverage.json`

Use the paper's default dimension weights (Math 0.35 / Visual 0.30 / Numeric 0.20 / Structural 0.15) unless the problem genuinely lacks a dimension — e.g. a pure-geometry problem might have minimal Numeric content, in which case redistribute weight rather than forcing a fit.

### Step 8 — Fill `version_notes.json`

Cross-check the code against all eight known GL→CE categories from the paper — import system, class configuration, scene types, animation renames, PiCreature ecosystem, 3D/depth rendering, camera control, custom mobjects — not just the one that's obviously present. Grep shortcut for the common ones:

```bash
grep -nE "ShowCreation|CONFIG = \{|self\.frame\.reorient|apply_depth_test|GraphScene|InteractiveScene" your_file.py
```

Every hit becomes a `version_notes.json` entry with severity `auto-fail if used`.

### Step 9 — Pull reference clip, embed, discard

```bash
yt-dlp --download-sections "*<start>-<end>" -f mp4 "https://youtu.be/<video_id>" -o clip.mp4
ffmpeg -i clip.mp4 -vf fps=2 frames/%03d.png
python scripts/extract_and_embed_frames.py --frames frames/ --out data/problems/MB-XXX/ref_embeddings.npy
rm -rf clip.mp4 frames/
```

No `.mp4` or `.png` should ever land in `data/` — only the embedding.

### Step 10 — Validate and register

- Run `validate_dataset.py`: schema check, weights sum to 1.0, every path referenced in `problem.json` actually resolves, no empty `keyword_bank`/`clip_query`.
- Add or update the entry in `metadata.json`.
- Once you're not the only annotator, reuse the paper's own disagreement protocol — two independent passes, third reviewer resolves any gap greater than 0.15 — applied to the *annotation* itself (not just alignment grading) to keep problems consistent as the set scales past the 12-problem pilot.

---

## 4. Pre-submit QA checklist

- [ ] `full_prompt` contains no Scene/class/method names
- [ ] `visual_events` weights sum to 1.0
- [ ] every event has a non-empty `keyword_bank` **and** `clip_query`
- [ ] `keyword_bank` terms are CE vocabulary, not GL vocabulary
- [ ] all 8 version-conflict categories checked, not just the obvious one
- [ ] no raw video frames or `.mp4` committed anywhere under `data/`
- [ ] difficulty label matches the rubric in §3 Step 5, not a gut feeling
- [ ] `metadata.json` updated

---

## 5. Suggested attribution block (for dataset README / HF card)

> Problem prompts, visual event specifications, and reward-model annotations are original work. Reference code analysis is derived from `3b1b/videos` (© Grant Sanderson / 3Blue1Brown, licensed CC BY-NC-SA 4.0); no source code or video frames are redistributed in this dataset. Video source: the 3Blue1Brown YouTube channel. This dataset is intended for non-commercial research use.
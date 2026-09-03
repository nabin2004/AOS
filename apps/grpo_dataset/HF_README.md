---
pretty_name: ManiBench GRPO Reference Scenes
license: cc-by-nc-sa-4.0
task_categories:
  - text-generation
language:
  - en
tags:
  - manim
  - manimgl
  - animation
  - mathematics
  - code
  - grpo
  - 3blue1brown
size_categories:
  - n<1K
---

# ManiBench GRPO Reference Scenes

200 cleaned **ManimGL** scene excerpts for GRPO / reward-model work on math animation code. Each problem is a folder `data/problems/MB-XXX/` with a `reference.py` extracted from [3b1b/videos](https://github.com/3b1b/videos) (years 2022–2026).

This release is **reference code only**. Prompt, visual-event, coverage, and version-note JSON files are empty placeholders to fill later. CLIP embeddings and raw video are not included.

**Not in this set:** the 12 ManiBench pilot / benchmark videos (colliding blocks, gradient descent, convolution, eigenvectors, determinant, CLT, medical test, chain rule, integration / Gaussian integral, Taylor series, hairy ball, windmill).

## Dataset structure

```text
data/
  problems/
    MB-001/ … MB-200/
      reference.py          # cleaned ManimGL scene + helpers
      problem.json          # empty (to annotate)
      visual_events.json    # empty
      coverage.json         # empty
      version_notes.json    # empty
  reference_index.json      # id → source path, class, year, topic
scripts/
  curated_scenes.json       # locked 200-row selection
```

Load the index:

```python
from datasets import load_dataset
import json
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="nabin2004/manibench-grpo",
    repo_type="dataset",
    filename="data/reference_index.json",
)
index = json.loads(open(path, encoding="utf-8").read())
print(len(index), index[0])
```

Download a scene:

```python
from huggingface_hub import hf_hub_download

ref = hf_hub_download(
    repo_id="nabin2004/manibench-grpo",
    repo_type="dataset",
    filename="data/problems/MB-113/reference.py",
)
print(open(ref, encoding="utf-8").read()[:500])
```

## Composition

| Year | Count |
|------|------:|
| 2026 | 40 |
| 2025 | 50 |
| 2024 | 45 |
| 2023 | 40 |
| 2022 | 25 |
| **Total** | **200** |

Topics include cross-entropy, print gallery / conformal maps, spheres, cosmic distance, Grover / quantum, Laplace transforms, transformers, holograms, inscribed-rectangle topology, optics, Moser, quintic / Galois, Fourier/piano, Borwein integrals, and visual proofs. Scenes were scored for pedagogical visual math (multiple `play()` beats, axes, Tex, trackers, 3D) and exclude Pi-creature classroom dialogue, thumbnails, and SoME announcements.

`reference.py` keeps ManimGL APIs (`ShowCreation`, `Tex`, `self.frame.reorient`, …). It is not a Community Edition port.

## License and attribution

Reference excerpts are derived from **[3b1b/videos](https://github.com/3b1b/videos)** © Grant Sanderson / 3Blue1Brown, licensed [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). This dataset inherits those terms: attribution required, **non-commercial** use only, share-alike.

No YouTube video files or frames are redistributed. Engine code is *not* bundled; scenes expect `from manim_imports_ext import *` as in the 3b1b videos repo.

## Status

Annotation files (`problem.json`, `visual_events.json`, `coverage.json`, `version_notes.json`) are empty on purpose. Do not treat this snapshot as a finished GRPO training split until those fields are filled.

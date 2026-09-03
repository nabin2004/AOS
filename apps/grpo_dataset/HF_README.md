---
pretty_name: Manim GRPO Dataset 200
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

# Manim GRPO Dataset 200

200+ cleaned **ManimGL** scene excerpts and populated metadata bundles for GRPO / reward-model training on mathematical animation code. Each problem is a directory `data/problems/MB-XXX/` containing `reference.py` extracted from [3b1b/videos](https://github.com/3b1b/videos) (years 2022–2026), complete with `problem.json`, `visual_events.json`, `coverage.json`, `version_notes.json`, and `ref_embeddings.npy`.

## Dataset structure

```text
data/
  problems/
    MB-001/ … MB-200/
      reference.py          # cleaned ManimGL scene + helpers
      problem.json          # LLM synthesized prompt, domain, difficulty & code analysis
      visual_events.json    # weighted visual event timeline & CLIP queries
      coverage.json         # weighted category requirements
      version_notes.json    # ManimGL to CE API compatibility notes
      ref_embeddings.npy    # reference frame embeddings
  splits/
    train.jsonl             # 172 training items
    val.jsonl               # 21 validation items
    test.jsonl              # 22 test items
scripts/
  curated_scenes.json       # locked 200-row selection
```

Load the index / splits:

```python
from datasets import load_dataset
import json
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    repo_id="nabin2004/Manim-grpo-dataset-200",
    repo_type="dataset",
    filename="data/splits/train.jsonl",
)
```

Download a scene:

```python
from huggingface_hub import hf_hub_download

ref = hf_hub_download(
    repo_id="nabin2004/Manim-grpo-dataset-200",
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
| **Total** | **200+** |

Topics include cross-entropy, print gallery / conformal maps, spheres, cosmic distance, Grover / quantum, Laplace transforms, transformers, holograms, inscribed-rectangle topology, optics, Moser, quintic / Galois, Fourier/piano, Borwein integrals, and visual proofs. Scenes were scored for pedagogical visual math (multiple `play()` beats, axes, Tex, trackers, 3D) and exclude Pi-creature classroom dialogue, thumbnails, and SoME announcements.

`reference.py` keeps ManimGL APIs (`ShowCreation`, `Tex`, `self.frame.reorient`, …).

## Narration and Multi-Modal Reward Integration

The reward pipeline includes a specialized **Narration Scoring** component (`reward_model/narration.py`) designed for Manim Voiceover GRPO fine-tuning. It provides dense rewards for:
- `VoiceoverScene` structure and lifecycle methods
- Speech service binding via `self.set_speech_service(...)`
- Multi-beat `self.voiceover(...)` blocks
- SSML bookmarks (`<bookmark mark="..." />`) and synchronization points (`self.wait_until_bookmark(...)`)

## License and attribution

Reference excerpts are derived from **[3b1b/videos](https://github.com/3b1b/videos)** © Grant Sanderson / 3Blue1Brown, licensed [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). This dataset inherits those terms: attribution required, **non-commercial** use only, share-alike.


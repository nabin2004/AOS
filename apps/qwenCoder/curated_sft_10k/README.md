---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
  - manim
  - code-generation
  - sft
size_categories:
  - 1K<n<10K
---

# manim-sft-10k

Curated 10k Manim Community Edition chat SFT mix. Filtered from [`nabin2004/manim-sft`](https://huggingface.co/datasets/nabin2004/manim-sft) with a static API-signature linter (no full render pass), then mixed with synthetic API-grounding, error-correction, and LaTeX rows that target ManiBench failures (invalid kwargs, Unicode subscripts, NameError, sparse coverage).

The original 38k corpus is unchanged.

## Mix

| Bucket | Rows |
|--------|------|
| `long_scene` | 2000 |
| `latex` | 700 |
| `coverage_rich` | 2500 |
| `stratified_rest` | 2638 |
| `api_grounding` | 800 |
| `error_correction` | 1362 |
| **total** | **10000** |

## Schema

Chat `messages` (system / user / assistant) plus `metadata.bucket`.

```python
from datasets import load_dataset
ds = load_dataset("nabin2004/manim-sft-10k", split="train")
```


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

Curated 10k Manim Community Edition chat SFT mix. Filtered from
[`nabin2004/manim-sft`](https://huggingface.co/datasets/nabin2004/manim-sft)
with a static API-signature linter (no full render pass), then mixed with
synthetic API-grounding, error-correction, and LaTeX rows that target
ManiBench failures (invalid kwargs, Unicode subscripts, NameError, sparse coverage).

The original 38k corpus is unchanged.

**Dataset URL:** https://huggingface.co/datasets/nabin2004/manim-sft-10k

## Mix

| Bucket | Target | Role |
|--------|--------|------|
| `api_grounding` | 800 | Short valid constructors (Axes, Matrix, NumberLine, …) |
| `error_correction` | 1,500 | Broken code + truncated traceback → fixed scene |
| `latex` | 700 | Spoken math → `MathTex` with `w_1`, never `w₁` |
| `long_scene` | 2,000 | Lint-clean long scenes (scope / many `play`s) |
| `coverage_rich` | 2,500 | `LaggedStart`, multi-`Transform`, layered fades |
| `stratified_rest` | 2,500 | Length-binned remainder of lint-clean source |

Build locally:

```bash
cd apps/qwenCoder
uv run python curate_sft_10k.py --push --repo-id nabin2004/manim-sft-10k
```

## Schema

Chat `messages` (system / user / assistant) plus `metadata.bucket`.

```python
from datasets import load_dataset

ds = load_dataset("nabin2004/manim-sft-10k", split="train")
```

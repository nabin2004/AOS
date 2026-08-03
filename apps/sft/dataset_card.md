---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
  - manim
  - code-generation
  - animation
  - sft
size_categories:
  - 10K<n<100K
---

# manim-sft (primary training dataset)

TRL-ready supervised fine-tuning corpus of Manim animation instruction pairs in chat `messages` format.

**Dataset URL:** https://huggingface.co/datasets/nabin2004/manim-sft

## Files

| File | Format | Use |
|------|--------|-----|
| `data/train.jsonl` | Chat `messages` (system → user → assistant) | **Default SFT input** via [`apps/sft`](https://github.com/nabin2004/AOS/tree/master/apps/sft) |

38,491 rows. Each assistant turn is full Manim Python source (`from manim import *`).

## Schema

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "source": "huggingface-dataset-id",
    "quality_tier": "high|medium|standard"
  }
}
```

## Usage

### Load with datasets

```python
from datasets import load_dataset

ds = load_dataset("nabin2004/manim-sft", split="train")
print(len(ds), ds[0]["messages"][1]["role"])
```

### Train with AOS SFT

```bash
cd apps/sft
uv run python run.py
```

---

# AOS-Trajectories (legacy)

Code Agent tool-calling trajectories collected from the AOS pipeline.

**Dataset URL:** https://huggingface.co/datasets/nabin2004/AOS-Trajectories

## Files

| File | Format | Use |
|------|--------|-----|
| `trajectories.jsonl` | Raw agent trajectories | Legacy SFT via `--dataset-repo nabin2004/AOS-Trajectories` |
| `tool_trace/train.jsonl` | OpenAI-style multi-turn `messages` | Tool-use / CodeMode finetuning |
| `tool_trace/val.jsonl` | Same schema, held-out split | Validation |
| `metadata.jsonl` | Run metadata | Filtering / analysis |

## Raw trajectory schema (`trajectories.jsonl`)

One JSON object per line:

- `user_prompt` — user task
- `trajectory` — list of `{type, tool_name, input, output, is_error}` tool steps
- `final_code` — successful Manim Python script
- `summary` — optional narration text
- `success` — boolean
- `run_dir`, `timestamp`, `usage`, etc.

## Tool trace schema (`tool_trace/*.jsonl`)

OpenAI-compatible multi-turn format:

```json
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}
  ]
}
```

## Usage

### Load raw trajectories (default SFT)

```python
from datasets import load_dataset

ds = load_dataset(
    "json",
    data_files="hf://datasets/nabin2004/AOS-Trajectories/trajectories.jsonl",
    split="train",
)
```

Or with the AOS SFT trainer:

```bash
cd apps/sft
uv run python run.py
```

### Load tool trace split

```python
train = load_dataset(
    "json",
    data_files="hf://datasets/nabin2004/AOS-Trajectories/tool_trace/train.jsonl",
    split="train",
)
```

## Collection

Trajectories are collected from the AOS Code Agent (`coder_agent.py`) via `collect_traces.py` and exported with `export_local_sft.py`. Scale-up target for LoRA SFT: ~8k synthetic prompts → ~5k compile-ok trajectories (`sft_data_gen/run_waves.sh` + `status.py`). See the [AOS agents README](https://github.com/nabin2004/AOS/blob/master/apps/agents/README.md#sft-data-collection-code-agent) and [`sft_data_gen/README.md`](https://github.com/nabin2004/AOS/blob/master/apps/agents/sft_data_gen/README.md).

## Related

- [ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench) — GRPO reward benchmark (Phase 2)
- [AOS repository](https://github.com/nabin2004/AOS)

---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
  - manim
  - code-generation
  - tool-use
  - animation
  - sft
size_categories:
  - n<1K
---

# AOS-Trajectories

Code Agent tool-calling trajectories for fine-tuning LLMs on Manim animation generation (AOS project).

**Dataset URL:** https://huggingface.co/datasets/nabin2004/AOS-Trajectories

## Files

| File | Format | Use |
|------|--------|-----|
| `trajectories.jsonl` | Raw agent trajectories | Phase 1 SFT via [`apps/sft`](https://github.com/nabin2004/AOS/tree/master/apps/sft) |
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

Trajectories are collected from the AOS Code Agent (`coder_agent.py`) via `collect_traces.py` and exported with `export_local_sft.py`. See the [AOS agents README](https://github.com/nabin2004/AOS/blob/master/apps/agents/README.md#sft-data-collection-code-agent).

## Related

- [ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench) — GRPO reward benchmark (Phase 2)
- [AOS repository](https://github.com/nabin2004/AOS)

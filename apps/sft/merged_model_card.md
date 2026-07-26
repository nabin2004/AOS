---
license: apache-2.0
base_model: google/gemma-4-E2B-it
library_name: transformers
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - gemma4
  - tool-use
  - code-generation
  - animation
  - sft
  - merged
---

# AOS Gemma 4 Manim SFT (Merged)

Full **merged bf16 weights** (LoRA baked into base) for Manim animation generation via multi-turn tool calling.

**Model URL:** https://huggingface.co/nabin2004/AOS-gemma4-manim-merged

## Related repos

| Artifact | Repo |
|----------|------|
| LoRA adapter | [nabin2004/AOS-gemma4-manim-sft](https://huggingface.co/nabin2004/AOS-gemma4-manim-sft) |
| GGUF (Ollama / llama.cpp) | [nabin2004/AOS-gemma4-manim-gguf](https://huggingface.co/nabin2004/AOS-gemma4-manim-gguf) |

## Base model

Merged from [google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it) and the [AOS Manim SFT LoRA adapter](https://huggingface.co/nabin2004/AOS-gemma4-manim-sft). Accept the Gemma license and set `HF_TOKEN` to download.

## Training data

Fine-tuned on [nabin2004/AOS-Trajectories](https://huggingface.co/datasets/nabin2004/AOS-Trajectories) using the AOS Phase 1 SFT trainer ([`apps/sft`](https://github.com/nabin2004/AOS/tree/master/apps/sft)).

## Usage

### Load with Transformers

```python
import os
import torch
from transformers import AutoModelForImageTextToText, AutoTokenizer

token = os.environ["HF_TOKEN"]
model_id = "nabin2004/AOS-gemma4-manim-merged"

tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
model = AutoModelForImageTextToText.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    token=token,
)
```

### vLLM

Serve as a regular model (no `--enable-lora` needed):

```bash
vllm serve nabin2004/AOS-gemma4-manim-merged --max-model-len 8192
```

### Ollama / local GGUF

Convert to GGUF or pull the pre-built [GGUF repo](https://huggingface.co/nabin2004/AOS-gemma4-manim-gguf). See [`apps/sft/export_gguf.py`](https://github.com/nabin2004/AOS/tree/master/apps/sft/export_gguf.py).

## How this was produced

```bash
cd apps/sft
uv run python merge_adapter.py \
  --adapter-dir ./gemma4-manim-ft \
  --output-dir ./gemma4-manim-merged \
  --push-to-hub
```

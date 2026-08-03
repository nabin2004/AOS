---
license: apache-2.0
base_model: google/gemma-4-31B-it
library_name: transformers
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - gemma4
  - gemma4-31b
  - tool-use
  - code-generation
  - animation
  - sft
  - merged
---

# AOS Gemma 4 31B Manim SFT (Merged)

Full **merged bf16 weights** (LoRA baked into base) for Manim animation generation via multi-turn tool calling.

**Model URL:** https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-merged

## Related repos

| Artifact | Repo |
|----------|------|
| LoRA adapter | [nabin2004/AOS-gemma4-31b-manim-sft](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-sft) |
| GGUF (Ollama / llama.cpp) | [nabin2004/AOS-gemma4-31b-manim-gguf](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-gguf) |

## Base model

Merged from [google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it) and the [AOS Manim SFT LoRA adapter](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-sft). Accept the Gemma license and set `HF_TOKEN` to download.

## Training data

Fine-tuned on [nabin2004/manim-sft](https://huggingface.co/datasets/nabin2004/manim-sft) using the AOS SFT trainer ([`apps/sft`](https://github.com/nabin2004/AOS/tree/master/apps/sft)).

## Usage

### Load with Transformers

```python
import os
import torch
from transformers import AutoModelForImageTextToText, AutoTokenizer

token = os.environ["HF_TOKEN"]
model_id = "nabin2004/AOS-gemma4-31b-manim-merged"

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
vllm serve nabin2004/AOS-gemma4-31b-manim-merged --max-model-len 16384
```

### Ollama / local GGUF

Convert to GGUF or pull the pre-built [GGUF repo](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-gguf). See [`apps/sft/export_gguf.py`](https://github.com/nabin2004/AOS/tree/master/apps/sft/export_gguf.py).

## How this was produced

```bash
cd apps/sft
uv run python merge_adapter.py \
  --adapter-dir ./gemma4-31b-manim-ft \
  --output-dir ./gemma4-31b-manim-merged \
  --push-to-hub
```

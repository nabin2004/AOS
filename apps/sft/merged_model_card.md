---
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-7B-Instruct
library_name: transformers
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - qwen2.5-coder
  - qwen25-coder-7b
  - tool-use
  - code-generation
  - animation
  - sft
  - merged
---

# AOS Qwen2.5-Coder-7B Manim SFT (Merged)

Full **merged bf16 weights** (LoRA baked into base) for Manim animation generation via multi-turn tool calling.

**Model URL:** https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-merged

## Related repos

| Artifact | Repo |
|----------|------|
| LoRA adapter | [nabin2004/AOS-qwen25-coder-7b-manim-sft](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-sft) |
| GGUF (Ollama / llama.cpp) | [nabin2004/AOS-qwen25-coder-7b-manim-gguf](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-gguf) |

## Base model

Merged from [Qwen/Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) and the [AOS Manim SFT LoRA adapter](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-sft).

## Training data

Fine-tuned on [nabin2004/AOS-Trajectories](https://huggingface.co/datasets/nabin2004/AOS-Trajectories) using the AOS Phase 1 SFT trainer ([`apps/sft`](https://github.com/nabin2004/AOS/tree/master/apps/sft)).

## Usage

### Load with Transformers

```python
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

token = os.environ.get("HF_TOKEN")
model_id = "nabin2004/AOS-qwen25-coder-7b-manim-merged"

tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    token=token,
)
```

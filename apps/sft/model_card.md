---
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-7B-Instruct
library_name: peft
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - lora
  - qwen2.5-coder
  - qwen25-coder-7b
  - tool-use
  - code-generation
  - animation
  - sft
---

# AOS Qwen2.5-Coder-7B Manim SFT (LoRA)

LoRA adapter fine-tuned on Code Agent trajectories for **Manim animation generation** via multi-turn tool calling (`run_code` + workspace tools).

**Model URL:** https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-sft

## Base model

This adapter is trained on top of [Qwen/Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) (Apache 2.0). See [`docs/MODEL_SELECTION.md`](docs/MODEL_SELECTION.md) for the selection rationale.

## Training data

Fine-tuned on [nabin2004/AOS-Trajectories](https://huggingface.co/datasets/nabin2004/AOS-Trajectories) using the AOS Phase 1 SFT trainer ([`apps/sft`](https://github.com/nabin2004/AOS/tree/master/apps/sft)).

## Usage

### Load with PEFT (Python)

```python
import os
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

token = os.environ.get("HF_TOKEN")
base_id = "Qwen/Qwen2.5-Coder-7B-Instruct"
adapter_id = "nabin2004/AOS-qwen25-coder-7b-manim-sft"

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

base = AutoModelForCausalLM.from_pretrained(
    base_id,
    quantization_config=bnb,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    token=token,
)
model = PeftModel.from_pretrained(base, adapter_id, token=token)
tokenizer = AutoTokenizer.from_pretrained(adapter_id, token=token)
model.eval()
```

### Inference with AOS tool loop

The adapter is trained on **multi-turn Code Agent tool calls**, not single-turn prose. Use the AOS inference script:

```bash
cd apps/sft
uv run python infer.py \
  --adapter-dir nabin2004/AOS-qwen25-coder-7b-manim-sft \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

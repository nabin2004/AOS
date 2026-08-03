---
license: apache-2.0
base_model: google/gemma-4-31B-it
library_name: peft
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - lora
  - gemma4
  - gemma4-31b
  - tool-use
  - code-generation
  - animation
  - sft
---

# AOS Gemma 4 31B Manim SFT (LoRA)

LoRA adapter fine-tuned on Code Agent trajectories for **Manim animation generation** via multi-turn tool calling (`run_code` + workspace tools).

**Model URL:** https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-sft

## Base model

This adapter is trained on top of [google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it). You must accept the Gemma license and set `HF_TOKEN` to download the base weights.

## Training data

Fine-tuned on [nabin2004/manim-sft](https://huggingface.co/datasets/nabin2004/manim-sft) using the AOS SFT trainer ([`apps/sft`](https://github.com/nabin2004/AOS/tree/master/apps/sft)).

## Usage

### Load with PEFT (Python)

```python
import os
import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

token = os.environ["HF_TOKEN"]
base_id = "google/gemma-4-31B-it"
adapter_id = "nabin2004/AOS-gemma4-31b-manim-sft"

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

base = AutoModelForImageTextToText.from_pretrained(
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
  --adapter-dir nabin2004/AOS-gemma4-31b-manim-sft \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Colab:

```bash
uv run --package sft python apps/sft/infer.py \
  --adapter-dir nabin2004/AOS-gemma4-31b-manim-sft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

## Files

| File | Description |
|------|-------------|
| `adapter_config.json` | PEFT LoRA configuration |
| `adapter_model.safetensors` | LoRA weights |
| `tokenizer_config.json` | Training chat template (includes `{% generation %}` markers) |

## Training

```bash
cd apps/sft
uv run python run.py --epochs 2 --report-to wandb --push-to-hub
```

Or upload an existing adapter:

```bash
export HF_TOKEN=hf_...
uv run python upload_adapter.py --adapter-dir ./gemma4-31b-manim-ft
```

## Related

- [AOS-Trajectories dataset](https://huggingface.co/datasets/nabin2004/AOS-Trajectories)
- [ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench) — GRPO benchmark (Phase 2)
- [AOS repository](https://github.com/nabin2004/AOS)

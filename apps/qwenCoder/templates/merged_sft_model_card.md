---
license: apache-2.0
base_model: Qwen/Qwen3-8B
library_name: transformers
pipeline_tag: text-generation
language:
  - en
tags:
  - safetensors
  - sft
  - manim
  - manim-voiceover
  - aos
  - code-generation
  - math
---

# AOS Qwen3 8B Narrated (Continued SFT Merged)

This is the full **bf16 Safetensors** release of the Supervised Fine-Tuned (SFT) model for mathematical and scientific animation in **Manim Community Edition (CE)** synchronized with **manim-voiceover**.

- **Base Foundation Model**: `Qwen/Qwen3-8B`
- **Trained Adapter**: [`{hub_adapter_repo}`](https://huggingface.co/{hub_adapter_repo})
- **Merged Model**: [`{hub_merged_repo}`](https://huggingface.co/{hub_merged_repo})
- **Quantized GGUF Models**: [`{hub_gguf_repo}`](https://huggingface.co/{hub_gguf_repo})

---

## Model Capabilities

1. **VoiceoverScene Architecture**: Generates complete, executable Manim scripts inheriting from `VoiceoverScene`.
2. **Audio Bookmarking**: Integrates synchronized audio markers (`tracker.wait_until_bookmark(...)`) paired with visual animations.
3. **CE API Compliance**: Strict Manim Community Edition syntax, eliminating deprecated legacy APIs.

---

## Quickstart (vLLM / Transformers)

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "{hub_merged_repo}"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")

prompt = "Write a complete Manim VoiceoverScene explaining Bayes Theorem with visual probability trees."
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=2048, temperature=0.2)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

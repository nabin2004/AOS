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
  - manimce
  - aos
  - code-generation
  - math
---

# qwen-Manimator-1 (Merged bf16 Safetensors)

Full-weight merged release of **qwen-Manimator-1**, a Qwen/Qwen3-8B model fine-tuned
to generate pedagogically rich **ManimCE + Manim Voiceover** animations.

- **Base Model**: `Qwen/Qwen3-8B`
- **LoRA Adapter**: [`{hub_adapter_repo}`](https://huggingface.co/{hub_adapter_repo})
- **Merged Model**: [`{hub_merged_repo}`](https://huggingface.co/{hub_merged_repo})
- **Quantized GGUF**: [`{hub_gguf_repo}`](https://huggingface.co/{hub_gguf_repo})
- **Dataset**: [`nabin2004/qwen-Manimator-1-sft-data`](https://huggingface.co/datasets/nabin2004/qwen-Manimator-1-sft-data)

---

## Model Capabilities

1. **VoiceoverScene Architecture**: Generates complete, executable Manim scripts inheriting from `VoiceoverScene`.
2. **Audio Bookmarking**: Integrates `<bookmark mark='NAME'/>` tags + `self.wait_until_bookmark("NAME")` for audio-visual sync.
3. **CE API Compliance**: Strict Manim Community Edition syntax, no deprecated legacy APIs.
4. **Plan-then-Code**: Always outputs a `<Plan>` reasoning block followed by the Python implementation.

---

## Quickstart

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "{hub_merged_repo}"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")

messages = [
    {"role": "system", "content": "You are an expert Python programmer and mathematics educator specializing in ManimCE and Manim Voiceover. You create high-quality, pedagogically rich, narrated animations. You always use `VoiceoverScene`, `AOSSpeechService`, and precise bookmark timing."},
    {"role": "user", "content": "Create a Manim animation explaining Fourier series with audio narration."},
]
ids = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to("cuda")
out = model.generate(ids, max_new_tokens=2048, temperature=0.2, top_p=0.9, repetition_penalty=1.05)
print(tokenizer.decode(out[0][ids.shape[-1]:], skip_special_tokens=True))
```

---

## Training Config

| Parameter | Value |
|---|---|
| Base Model | `Qwen/Qwen3-8B` |
| Epochs | 3 |
| Max Length | 4500 |
| Learning Rate | 1e-4 |
| LoRA | r=16, alpha=32 |
| Optimizer | paged_adamw_8bit |
| Hardware | Kaggle T4×2 |

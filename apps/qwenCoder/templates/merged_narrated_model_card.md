---
license: apache-2.0
base_model: Qwen/Qwen3-8B
library_name: transformers
pipeline_tag: text-generation
language:
  - en
tags:
  - safetensors
  - dpo
  - preference
  - rlhf
  - manim
  - manim-voiceover
  - aos
  - code-generation
  - animation
  - merged
---

# AOS Qwen3 8B Narrated (DPO Aligned - Merged Safetensors)

Direct Preference Optimization (DPO) aligned full bf16 model for **Manim Community Edition** mathematical and educational animation synthesis with synchronized voiceover narration.

**Model Repository:** [{hub_merged_repo}](https://huggingface.co/{hub_merged_repo})

---

## Lineage & Provenance

| Role | Artifact / Repository | Description |
|---|---|---|
| **Base LLM** | [`Qwen/Qwen3-8B`](https://huggingface.co/Qwen/Qwen3-8B) | Base causal foundation model |
| **SFT Prior** | [`nabin2004/AOS-qwen3-8b-narrated-adapter`](https://huggingface.co/nabin2004/AOS-qwen3-8b-narrated-adapter) | Continued SFT on 400 synchronized educational voiceover trajectories |
| **DPO Adapter** | [`nabin2004/AOS-qwen3-8b-narrated-dpo`](https://huggingface.co/nabin2004/AOS-qwen3-8b-narrated-dpo) | Direct Preference Optimization adapter ($\beta=0.1$) |
| **Merged Weights** | [`{hub_merged_repo}`](https://huggingface.co/{hub_merged_repo}) | Full unquantized bfloat16 Safetensors weights (this repo) |
| **GGUF / Ollama** | [`{hub_gguf_repo}`](https://huggingface.co/{hub_gguf_repo}) | Multi-quantized GGUF (`Q4_K_M`, `Q8_0`) for Ollama & llama.cpp |

---

## Alignment Objective

The model was aligned with Direct Preference Optimization (DPO) to strongly prefer generating voiceover-synchronized educational animations:
- **Chosen**: Clean `VoiceoverScene` scripts with speech services (`AOSSpeechService` / `GTTSService`), animation duration tracking (`run_time=tracker.duration`), millisecond-accurate `<bookmark mark='...'/>` tags, and natural phonetic spoken narration.
- **Rejected**: Silent, un-narrated standard `Scene` code.

---

## Canonical Code Pattern

```python
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class SigmoidExplanation(VoiceoverScene):
    def construct(self):
        # Configure speech service
        self.set_speech_service(GTTSService())
        
        title = Title("The Sigmoid Activation Function")
        ax = Axes(x_range=[-6, 6, 2], y_range=[-0.2, 1.2, 0.5])
        curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=BLUE)
        dot = Dot(ax.c2p(0, 0.5), color=RED)

        with self.voiceover(
            text="Let's visualize the sigmoid function. <bookmark mark='AXES'/> We begin by setting up our coordinate system, <bookmark mark='CURVE'/> plotting the characteristic S-shaped curve, <bookmark mark='DOT'/> and marking the midpoint inflection at zero, point five."
        ) as tracker:
            self.play(Write(title))
            self.wait_until_bookmark("AXES")
            self.play(Create(ax))
            self.wait_until_bookmark("CURVE")
            self.play(Create(curve))
            self.wait_until_bookmark("DOT")
            self.play(FadeIn(dot), run_time=tracker.duration)
        self.wait(1)
```

---

## Quickstart Usage

### Hugging Face Transformers

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "{hub_merged_repo}"

tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

prompt = "Create a narrated Manim animation explaining the Fourier Transform with voiceover bookmarks."
messages = [
    {{"role": "system", "content": "You are an expert mathematical animation assistant specializing in Manim Community Edition and voiceover narration with manim-voiceover. You write complete, self-contained, fully executable Python scripts inheriting from VoiceoverScene."}},
    {{"role": "user", "content": prompt}}
]

text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer([text], return_tensors="pt").to(model.device)

outputs = model.generate(
    **inputs,
    max_new_tokens=2048,
    temperature=0.2,
    top_p=0.95,
    pad_token_id=tokenizer.eos_token_id,
)
print(tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True))
```

### High-Throughput Cloud Serving with vLLM

Serve as a high-performance OpenAI-compatible endpoint:

```bash
vllm serve {hub_merged_repo} \
    --port 8000 \
    --max-model-len 8192 \
    --trust-remote-code
```

---

## Citation & Acknowledgments

Part of the **AOS (Agentic Orchestration System)** project for multi-agent educational video synthesis.
- Base Model: Alibaba Cloud Qwen Team (`Qwen/Qwen3-8B`)
- Animation Engine: Manim Community Edition & `manim-voiceover`

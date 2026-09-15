---
license: apache-2.0
base_model: {hub_merged_repo}
library_name: gguf
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - manim-voiceover
  - gguf
  - ollama
  - llama.cpp
  - grpo
  - reinforcement-learning
  - aos
---

# AOS Qwen3 8B GRPO (GGUF Quantizations - Reinforcement Learning Release)

Quantized GGUF versions of the Group Relative Policy Optimization (GRPO) fine-tuned model for **Manim Community Edition** mathematical animation synthesis.

Trained via reinforcement learning on [ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench) and [Manim-grpo-dataset-200](https://huggingface.co/datasets/nabin2004/Manim-grpo-dataset-200) with visual and programmatic reward signals (VLM, AST syntax, visual coverage event rate, and execution success).

- **Merged Foundation Weights**: [`{hub_merged_repo}`](https://huggingface.co/{hub_merged_repo})
- **GRPO Adapter Source**: [`{hub_adapter_repo}`](https://huggingface.co/{hub_adapter_repo})

---

## Available Files & Quantizations

| File | Quantization | Size | Description |
|---|---|---|---|
| `{ollama_tag}-Q4_K_M.gguf` | Q4_K_M | ~5.03 GB | Recommended for fast consumer local inference (8GB+ RAM / VRAM). Balanced quality and throughput. |
| `{ollama_tag}-Q8_0.gguf` | Q8_0 | ~8.71 GB | Near-lossless 8-bit precision for high-fidelity code generation. |

---

## Quickstart with Ollama

### Option 1: Direct Run via Hugging Face Integration
```bash
ollama run hf.co/{hub_gguf_repo}
```

### Option 2: Using Local Model Tag
```bash
ollama run {ollama_tag}
```

### Option 3: Manual Import with Modelfile
```bash
huggingface-cli download {hub_gguf_repo} {ollama_tag}-Q4_K_M.gguf Modelfile --local-dir ./model
cd ./model
ollama create {ollama_tag} -f Modelfile
ollama run {ollama_tag}
```

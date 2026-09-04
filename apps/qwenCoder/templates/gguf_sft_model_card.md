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
  - sft
  - aos
---

# AOS Qwen3 8B Narrated (GGUF Quantizations - SFT Release)

Quantized GGUF versions of the Supervised Fine-Tuned (SFT) model for **Manim Community Edition** and **manim-voiceover** animation generation.

- **Merged Foundation Weights**: [`{hub_merged_repo}`](https://huggingface.co/{hub_merged_repo})
- **SFT Adapter Source**: [`{hub_adapter_repo}`](https://huggingface.co/{hub_adapter_repo})

---

## Available Files & Quantizations

| File | Quantization | Size | Description |
|---|---|---|---|
| `{ollama_tag}-Q4_K_M.gguf` | Q4_K_M | ~5.03 GB | Recommended for fast consumer local inference (8GB+ RAM / VRAM). |
| `{ollama_tag}-Q8_0.gguf` | Q8_0 | ~8.71 GB | Near-lossless 8-bit precision. |

---

## Quickstart with Ollama

### Option 1: Direct 1-Click Pull
```bash
ollama run hf.co/{hub_gguf_repo}
```

### Option 2: Using the Included Modelfile
```bash
huggingface-cli download {hub_gguf_repo} {ollama_tag}-Q4_K_M.gguf Modelfile --local-dir ./model
cd ./model
ollama create {ollama_tag} -f Modelfile
ollama run {ollama_tag}
```

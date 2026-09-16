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
  - manimce
  - gguf
  - ollama
  - llama.cpp
  - sft
  - aos
  - qwen3
---

# qwen-Manimator-1 GGUF Quantizations

Quantized GGUF versions of [`{hub_merged_repo}`](https://huggingface.co/{hub_merged_repo}),
a Qwen/Qwen3-8B SFT model for **ManimCE + Manim Voiceover** animation generation.

- **SFT Adapter Source**: [`{hub_adapter_repo}`](https://huggingface.co/{hub_adapter_repo})
- **Dataset**: [`nabin2004/qwen-Manimator-1-sft-data`](https://huggingface.co/datasets/nabin2004/qwen-Manimator-1-sft-data)

---

## Available Quantizations

| File | Quantization | Size | Description |
|---|---|---|---|
| `{ollama_tag}-Q4_K_M.gguf` | Q4_K_M | ~5.0 GB | Recommended for fast local inference (8 GB+ RAM/VRAM) |
| `{ollama_tag}-Q8_0.gguf` | Q8_0 | ~8.7 GB | Near-lossless 8-bit precision |

---

## Quickstart with Ollama

### Option 1: 1-Click Pull
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

### Option 3: Run from Merged Repo (has GGUF injected)
```bash
ollama run hf.co/{hub_merged_repo}
```

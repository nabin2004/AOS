---
license: apache-2.0
base_model: nabin2004/AOS-qwen25-coder-7b-manim-merged
library_name: gguf
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - qwen2.5-coder
  - qwen25-coder-7b
  - gguf
  - ollama
  - llama.cpp
  - tool-use
  - animation
  - sft
---

# AOS Qwen2.5-Coder-7B Manim SFT (GGUF)

**Q4_K_M** GGUF of the AOS Manim SFT merged model. Drop-in for **Ollama** and **llama.cpp**.

**Model URL:** https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-gguf

## Files

| File | Description |
|------|-------------|
| `aos-qwen25-coder-7b-manim-Q4_K_M.gguf` | Quantized weights (~4–5 GB for 7B) |
| `Modelfile` | Ollama import template |

## Related repos

| Artifact | Repo |
|----------|------|
| LoRA adapter | [nabin2004/AOS-qwen25-coder-7b-manim-sft](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-sft) |
| Merged HF weights | [nabin2004/AOS-qwen25-coder-7b-manim-merged](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-merged) |

## Ollama

```bash
ollama create aos-qwen25-coder-7b-manim -f Modelfile
ollama run aos-qwen25-coder-7b-manim
```

## llama.cpp

```bash
./llama-cli -m aos-qwen25-coder-7b-manim-Q4_K_M.gguf -p "Animate a unit circle."
```

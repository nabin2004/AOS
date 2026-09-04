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
  - dpo
  - aos
---

# AOS Qwen3 8B Narrated (GGUF - Ollama & llama.cpp)

Quantized **GGUF** format weights of the Direct Preference Optimization (DPO) aligned **AOS Qwen3 8B Narrated** model. Designed for local, zero-overhead execution via **Ollama**, **llama.cpp**, **LM Studio**, and **Jan**.

**Model Repository:** [{hub_gguf_repo}](https://huggingface.co/{hub_gguf_repo})

---

## Quantized Variants

| File | Quant Method | File Size | Recommended Hardware | Description |
|---|---|---|---|---|
| `aos-qwen3-8b-narrated-Q4_K_M.gguf` | `Q4_K_M` | ~5.0 GB | 8 GB+ RAM / VRAM | **Recommended default**: Fast execution, low memory footprint, high animation accuracy |
| `aos-qwen3-8b-narrated-Q8_0.gguf` | `Q8_0` | ~8.5 GB | 12 GB+ RAM / VRAM | Near-lossless 8-bit precision for complex multi-scene code logic |
| `Modelfile` | Config | < 1 KB | Any | Ollama container configuration template with prompt tuning |

---

## Quickstart with Ollama

### 1. Download & Build Local Model

```bash
# Clone the GGUF repository or download the Q4_K_M binary
huggingface-cli download {hub_gguf_repo} aos-qwen3-8b-narrated-Q4_K_M.gguf Modelfile --local-dir ./aos-narrated-gguf

cd ./aos-narrated-gguf
ollama create {ollama_tag} -f Modelfile
```

### 2. Run Interactively

```bash
ollama run {ollama_tag}
```

---

## OpenAI-Compatible Local Serving

Ollama automatically exposes an OpenAI-compatible REST server at `http://localhost:11434/v1`:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # dummy key
)

response = client.chat.completions.create(
    model="{ollama_tag}",
    messages=[
        {{"role": "system", "content": "You are an expert mathematical animation assistant specializing in Manim Community Edition and voiceover narration with manim-voiceover."}},
        {{"role": "user", "content": "Create a VoiceoverScene visualizing gradient descent on a parabola."}}
    ],
    temperature=0.2,
)

print(response.choices[0].message.content)
```

---

## Running with llama.cpp Server

```bash
./llama-server \
    -m aos-qwen3-8b-narrated-Q4_K_M.gguf \
    --port 8080 \
    -ngl 99 \
    -c 8192
```

---

## Lineage & Reference

- **Base Foundation Model:** [`Qwen/Qwen3-8B`](https://huggingface.co/Qwen/Qwen3-8B)
- **SFT Adapter Prior:** [`nabin2004/AOS-qwen3-8b-narrated-adapter`](https://huggingface.co/nabin2004/AOS-qwen3-8b-narrated-adapter)
- **DPO Adapter:** [`nabin2004/AOS-qwen3-8b-narrated-dpo`](https://huggingface.co/nabin2004/AOS-qwen3-8b-narrated-dpo)
- **Merged Full Weights:** [`{hub_merged_repo}`](https://huggingface.co/{hub_merged_repo})

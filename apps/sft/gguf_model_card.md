---
license: apache-2.0
base_model: nabin2004/AOS-gemma4-manim-merged
library_name: gguf
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - gemma4
  - gguf
  - ollama
  - llama.cpp
  - tool-use
  - animation
  - sft
---

# AOS Gemma 4 Manim SFT (GGUF)

**Q4_K_M** GGUF of the AOS Manim SFT merged model. Drop-in for **Ollama** and **llama.cpp**.

**Model URL:** https://huggingface.co/nabin2004/AOS-gemma4-manim-gguf

## Files

| File | Description |
|------|-------------|
| `aos-gemma4-manim-Q4_K_M.gguf` | Quantized weights (~2 GB for E2B) |
| `Modelfile` | Ollama import template |

## Related repos

| Artifact | Repo |
|----------|------|
| LoRA adapter | [nabin2004/AOS-gemma4-manim-sft](https://huggingface.co/nabin2004/AOS-gemma4-manim-sft) |
| Merged HF weights | [nabin2004/AOS-gemma4-manim-merged](https://huggingface.co/nabin2004/AOS-gemma4-manim-merged) |

## Ollama

Pull from Hugging Face or create locally from the downloaded GGUF:

```bash
ollama create aos-gemma4-manim -f Modelfile
ollama run aos-gemma4-manim
```

Requires **Ollama 0.30+** (native Gemma 4 support).

## OpenAI-compatible API

Ollama exposes `/v1/chat/completions` on port 11434:

```python
from gemma4_client import DEFAULT_OLLAMA_BASE_URL, Gemma4Client

client = Gemma4Client(
    model="aos-gemma4-manim",
    base_url=DEFAULT_OLLAMA_BASE_URL,
    api_key="ollama",
)
print(client.chat("Animate a unit circle morphing into an ellipse."))
```

See [`apps/server/README.md`](https://github.com/nabin2004/AOS/tree/master/apps/server/README.md).

## llama.cpp

```bash
./llama-server -m aos-gemma4-manim-Q4_K_M.gguf --chat-template gemma --port 8080
```

## How this was produced

```bash
cd apps/sft
export LLAMA_CPP_DIR=~/llama.cpp
uv run python export_gguf.py \
  --model-dir ./gemma4-manim-merged \
  --output-dir ./gemma4-manim-gguf \
  --push-to-hub
```

Quantization chain: `merge_adapter.py` → `convert_hf_to_gguf.py` (F16) → `llama-quantize Q4_K_M`.

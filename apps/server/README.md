# server

A small client for Gemma 4 models served through [vLLM](https://github.com/vllm-project/vllm)'s
OpenAI-compatible API. Gemma 4 is a multimodal model family (text, image, audio) with thinking
mode, function calling, and structured outputs; `gemma4_client.py` wraps those capabilities so
callers don't have to hand-build request payloads.

This package is only the client. The vLLM server itself runs as a separate process (locally, in
Docker, or on TPU/AMD hardware) — see [Launching a server](#launching-a-server) below.

## Install

```bash
uv sync --package server
```

## Quick start

```python
from gemma4_client import Gemma4Client

client = Gemma4Client(model="google/gemma-4-31B-it")
print(client.chat("Write a short poem about the ocean."))
```

For LoRA adapters trained in [`apps/sft`](../sft/) (base model `google/gemma-4-31B-it`), pass the
LoRA module name registered with vLLM:

```python
from gemma4_client import Gemma4Client

client = Gemma4Client(adapter="manim-sft")
print(client.list_models())  # verify manim-sft appears
print(client.chat("Explain gradient descent briefly."))
```

Run the bundled demo (requires a server already running on `localhost:8000`):

```bash
uv run --package server python apps/server/main.py
uv run --package server python apps/server/main.py --adapter manim-sft
uv run --package server python apps/server/main.py --list-models
```

## Ollama (GGUF export)

After merging and exporting with [`apps/sft/export_gguf.py`](../sft/export_gguf.py), Ollama serves
the model on its OpenAI-compatible API at `http://localhost:11434/v1`.

```bash
# Create model (if export_gguf.py was run with --skip-ollama-create)
ollama create aos-gemma4-31b-manim -f ./gemma4-31b-manim-gguf/Modelfile
ollama run aos-gemma4-31b-manim
```

```python
from gemma4_client import DEFAULT_OLLAMA_BASE_URL, DEFAULT_OLLAMA_MODEL, Gemma4Client

client = Gemma4Client(
    model=DEFAULT_OLLAMA_MODEL,
    base_url=DEFAULT_OLLAMA_BASE_URL,
    api_key="ollama",
)
print(client.chat("Create a Manim scene explaining eigenvectors."))
```

CLI demo:

```bash
uv run --package server python apps/server/main.py \
  --base-url http://localhost:11434/v1 \
  --model aos-gemma4-31b-manim \
  --api-key ollama \
  --prompt "Animate a unit circle morphing into an ellipse."
```

Smoke test with curl:

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"aos-gemma4-31b-manim","messages":[{"role":"user","content":"Hello"}]}'
```

Tool calling works when the GGUF carries tool metadata — verify with `ollama show aos-gemma4-31b-manim`.
Use `client.call_with_tools(...)` the same way as with vLLM.

## API

All methods take `max_tokens` and forward extra `**kwargs` straight to the underlying
`chat.completions.create` call.

| Method | Purpose |
| --- | --- |
| `list_models()` | List model ids from the vLLM `/v1/models` endpoint (includes registered LoRA modules) |
| `chat(prompt_or_messages)` | Plain text chat completion |
| `think(prompt_or_messages)` | Chat completion with thinking mode; returns `ThinkingResult(content, reasoning)` |
| `describe_images(image_urls, prompt, vision_tokens=None)` | Ask about one or more images; `vision_tokens` is one of `70, 140, 280, 560, 1120` |
| `transcribe_audio(audio_url, prompt=...)` | Transcribe or answer questions about audio (E2B/E4B models only) |
| `describe_video(video_url, prompt)` | Ask about a video |
| `call_with_tools(messages, tools)` | Chat turn with tool definitions; returns the raw response message so you can inspect `.tool_calls` and feed results back |
| `structured(prompt_or_messages, schema, schema_name="response")` | Chat completion constrained to a JSON schema (dict or Pydantic model class) |

`prompt_or_messages` accepts either a plain string or a full `messages` list when you need
multi-turn history or a system prompt.

Structured output notes: the schema only enforces shape (keys, types, required fields) — the
model never sees field descriptions. Put semantic instructions (units, formatting rules) in the
prompt itself.

## LoRA / QLoRA adapters

LoRA and QLoRA fine-tuning for Manim trajectory SFT lives in [`apps/sft`](../sft/). Training
uses **QLoRA** (4-bit NF4) for memory efficiency; **serving** loads bf16 base weights plus LoRA
adapter weights through vLLM — not the 4-bit training checkpoint.

Default SFT base model: `google/gemma-4-31B-it`. Published adapter:
[`nabin2004/AOS-gemma4-31b-manim-sft`](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-sft).

### Launch vLLM with a LoRA adapter

Register the adapter at server startup with `--enable-lora` and `--lora-modules`. The left-hand
name is what you pass to `Gemma4Client(adapter=...)`:

```bash
vllm serve google/gemma-4-31B-it \
  --enable-lora \
  --max-lora-rank 64 \
  --lora-modules manim-sft=nabin2004/AOS-gemma4-31b-manim-sft \
  --max-model-len 8192 \
  --host 0.0.0.0 \
  --port 8000
```

Local adapter directory (output from `apps/sft/run.py`):

```bash
vllm serve google/gemma-4-31B-it \
  --enable-lora \
  --max-lora-rank 64 \
  --lora-modules manim-sft=./gemma4-31b-manim-ft \
  --max-model-len 8192 \
  --host 0.0.0.0 \
  --port 8000
```

If generation formatting differs from the base template, point vLLM at the SFT chat template:

```bash
  --chat-template ../sft/templates/gemma4_training.jinja
```

### Client usage

```python
from gemma4_client import Gemma4Client

client = Gemma4Client(adapter="manim-sft")
print(client.list_models())
print(client.chat("Explain gradient descent briefly."))
```

Use the **LoRA module name** (e.g. `manim-sft`) as `adapter` — not the Hugging Face repo id.
The base model passed to `vllm serve` must match the adapter's training run.

### Notes

- Gemma 4 LoRA in vLLM requires a recent vLLM build (around v0.19+). If `--enable-lora` fails,
  upgrade vLLM or merge the adapter with [`apps/sft/merge_adapter.py`](../sft/merge_adapter.py)
  and serve the merged checkpoint as a regular model.
- For multi-turn Manim tool calling (`run_code` → workspace tools), use
  [`apps/sft/infer.py`](../sft/infer.py) instead of plain `chat()` — the SFT adapter is trained
  on tool trajectories, not single-turn prose.

## Launching a server

### Installing vLLM (separate environment)

vLLM is **not** a dependency of this package. The client only needs `openai`; the inference server
runs as its own process. Do not run `uv add vllm` inside the AOS workspace — vLLM pins
`torch==2.11.0` while the workspace locks `torch==2.12.1` for `agents`/`sft`/`grpo`, and uv may
backtrack to ancient source-only vLLM releases that fail to build without CUDA.

Install vLLM in a dedicated environment instead (Gemma 4 LoRA needs **vLLM >= 0.19**):

```bash
# GPU (NVIDIA / AMD / TPU) — standard wheel
uv venv ~/.venvs/aos-vllm --python 3.12
source ~/.venvs/aos-vllm/bin/activate
uv pip install "vllm>=0.19"

# CPU-only laptop — must use the CPU wheel (GPU wheel fails with "Failed to infer device type")
./apps/server/scripts/install-vllm-cpu.sh
```

Or install the CPU wheel manually:

```bash
uv venv ~/.venvs/aos-vllm --python 3.12
source ~/.venvs/aos-vllm/bin/activate
uv pip uninstall vllm  # drop GPU build if present
uv pip install \
  "https://github.com/vllm-project/vllm/releases/download/v0.26.0/vllm-0.26.0+cpu-cp38-abi3-manylinux_2_34_x86_64.whl" \
  --torch-backend cpu
./apps/server/scripts/repair-vllm-cpu.sh   # force +cpu torchvision/torchaudio too
```

Always pass `--torch-backend cpu` for the vLLM wheel **and** the torch/torchvision/torchaudio
triplet — otherwise uv may install CUDA `torchvision` alongside CPU `torch`.

For Docker, TPU, or AMD deployment, see [vLLM's Gemma 4 docs](https://docs.vllm.ai/) and
[vLLM CPU install docs](https://docs.vllm.ai/en/stable/getting_started/installation/cpu/).

### CPU-only dev (smoke tests)

CPU inference is **very slow** (seconds per token) and memory-heavy — fine for checking that the
client and LoRA wiring work, not for real generation. On a 8–16 GiB laptop, keep
`VLLM_CPU_KVCACHE_SPACE` low and reduce `--max-model-len` if you OOM.

```bash
source ~/.venvs/aos-vllm/bin/activate
./apps/server/scripts/serve-cpu.sh

# More RAM free? give the KV cache a bit more headroom:
VLLM_CPU_KVCACHE_SPACE=4 MAX_MODEL_LEN=8192 ./apps/server/scripts/serve-cpu.sh
```

Equivalent manual launch:

```bash
export VLLM_CPU_KVCACHE_SPACE=2          # GiB for KV cache; increase if you have RAM to spare
export VLLM_CPU_OMP_THREADS_BIND=auto
vllm serve google/gemma-4-31B-it \
  --enable-lora \
  --max-lora-rank 64 \
  --lora-modules manim-sft=nabin2004/AOS-gemma4-31b-manim-sft \
  --max-model-len 4096 \
  --dtype bfloat16 \
  --host 0.0.0.0 \
  --port 8000
```

On Linux, preloading tcmalloc can help CPU throughput (`gperftools` on Arch,
`libtcmalloc-minimal4` on Debian). See vLLM's CPU docs for `LD_PRELOAD` setup.

For CPU-only LoRA inference without the vLLM server, use
[`apps/sft/infer.py`](../sft/infer.py) (Transformers + PEFT, runs on CPU with less overhead).

#### Troubleshooting (CPU)

| Symptom | Fix |
| --- | --- |
| `Failed to infer device type` | GPU vLLM wheel on a CPU-only machine — run `./apps/server/scripts/install-vllm-cpu.sh` |
| `operator torchvision::nms does not exist` | CPU `torch` but CUDA/generic `torchvision` — run `./apps/server/scripts/repair-vllm-cpu.sh` |
| OOM during model load | Lower `VLLM_CPU_KVCACHE_SPACE` (e.g. `2`) and `MAX_MODEL_LEN` (e.g. `4096`) |

Manual repair for the torchvision mismatch:

```bash
source ~/.venvs/aos-vllm/bin/activate
uv pip uninstall torchvision torchaudio -y
uv pip install torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0 --torch-backend cpu --reinstall
```

The `CUDA_HOME` error from `uv add vllm` inside the workspace is a separate issue — uv backtracks
to an ancient source-only vLLM release. Use the dedicated venv above instead.

The client talks to any vLLM server exposing the Gemma 4 chat completions API. Minimal example:

```bash
vllm serve google/gemma-4-31B-it --max-model-len 16384
```

Enable the extra capabilities the client supports:

| Capability | Required server flags |
| --- | --- |
| Thinking mode | `--reasoning-parser gemma4` |
| Tool calling | `--enable-auto-tool-choice --tool-call-parser gemma4` |
| Audio | `vllm[audio]` extra installed, plus `--limit-mm-per-prompt audio=1` |
| Video | `--limit-mm-per-prompt video=1` |
| Vision token budget | `--mm-processor-kwargs '{"max_soft_tokens": N}'` sets the default (`N` in `70,140,280,560,1120`) |

Full-featured launch (text, image, audio, thinking, tool calling):

```bash
vllm serve google/gemma-4-31B-it \
  --tensor-parallel-size 2 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  --enable-auto-tool-choice \
  --reasoning-parser gemma4 \
  --tool-call-parser gemma4 \
  --chat-template examples/tool_chat_template_gemma4.jinja \
  --limit-mm-per-prompt image=4,audio=1 \
  --async-scheduling \
  --host 0.0.0.0 \
  --port 8000
```

### Supported models

| Model | Params | Min NVIDIA GPU (BF16) | HuggingFace |
| --- | --- | --- | --- |
| Gemma 4 E2B IT | effective 2B | 1× 24 GB+ | `google/gemma-4-E2B-it` |
| Gemma 4 E4B IT | effective 4B | 1× 24 GB+ | `google/gemma-4-E4B-it` |
| Gemma 4 31B IT | 31B | 1× 80 GB | `google/gemma-4-31B-it` |
| Gemma 4 26B-A4B IT (MoE) | 26B / 4B active | 1× 80 GB | `google/gemma-4-26B-A4B-it` |

E2B and E4B also support audio. All sizes run on NVIDIA, AMD (MI300X/MI325X/MI350X/MI355X), and
Google Cloud TPU (Trillium/Ironwood).

Installing vLLM, Docker images, and TPU/AMD deployment steps are covered in vLLM's own Gemma 4
docs — this README covers only what's needed to point the client at a running server.

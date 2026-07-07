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

Run the bundled demo (requires a server already running on `localhost:8000`):

```bash
uv run --package server python apps/server/main.py
```

## API

All methods take `max_tokens` and forward extra `**kwargs` straight to the underlying
`chat.completions.create` call.

| Method | Purpose |
| --- | --- |
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

## Launching a server

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

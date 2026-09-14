"""
Deploy nabin2004/AOS-qwen3-8b-narrated-sft-merged on Modal
as an OpenAI-compatible API using vLLM.

Usage:
    modal setup                       # one-time auth
    modal deploy aos_deploy.py        # deploy persistently
    modal run aos_deploy.py           # spin up + smoke-test, tear down after

Docs: https://modal.com/docs/guide
Reference example this is adapted from:
https://modal.com/docs/examples/vllm_inference
"""             

import os
import json
from typing import Any

import aiohttp
import modal

try:
    from huggingface_hub import get_token
    HF_TOKEN = os.environ.get("HF_TOKEN") or get_token() or ""
except Exception:
    HF_TOKEN = os.environ.get("HF_TOKEN") or ""

# -----------------------------------------------------------------------
# Container image
# -----------------------------------------------------------------------
vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0", "peft", "transformers", "huggingface_hub")
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",  # faster weight transfers from the HF Hub
            "VLLM_LOG_STATS_INTERVAL": "1",
        }
    )
)

# -----------------------------------------------------------------------
# Model config
# -----------------------------------------------------------------------
MODEL_NAME = "nabin2004/AOS-qwen3-8b-grpo-merged"
SERVED_MODEL_NAME = "nabin2004/AOS-qwen3-8b-grpo"  # primary name clients will request

# Weight cache so we don't re-download the ~16GB safetensors file on every cold start
hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)

# Set True for faster cold starts (skips torch.compile / CUDA graph capture),
# or False for best steady-state throughput once warm.
FAST_BOOT = True

app = modal.App("aosqwen")

N_GPU = 1
MINUTES = 60
VLLM_PORT = 8000
GPU = "L40S"

secrets_list = [modal.Secret.from_dict({"HF_TOKEN": HF_TOKEN})] if HF_TOKEN else []


@app.function(
    image=vllm_image,
    gpu=f"{GPU}:{N_GPU}",
    timeout=30 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
    },
    secrets=secrets_list,
)
def merge_and_push_model(
    base_model_id: str = "Qwen/Qwen3-8B",
    adapter_id: str = "nabin2004/AOS-qwen3-8b-grpo",
    target_repo_id: str = "nabin2004/AOS-qwen3-8b-grpo-merged",
):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    token = os.environ.get("HF_TOKEN")
    print(f"Starting merge of {base_model_id} + {adapter_id} -> {target_repo_id}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, token=token, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        token=token,
        trust_remote_code=True,
    )
    print("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, adapter_id, token=token)
    print("Merging and unloading LoRA weights...")
    merged = model.merge_and_unload()

    print(f"Pushing merged model to Hugging Face Hub: {target_repo_id}...")
    merged.push_to_hub(target_repo_id, token=token, private=False)
    tokenizer.push_to_hub(target_repo_id, token=token, private=False)
    print(f"✔ Merged model successfully pushed to https://huggingface.co/{target_repo_id}!")
    return f"https://huggingface.co/{target_repo_id}"


@app.server(
    image=vllm_image,
    gpu=f"{GPU}:{N_GPU}",
    scaledown_window=15 * MINUTES,
    startup_timeout=10 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    port=VLLM_PORT,
    target_concurrency=32,
    unauthenticated=True,
    secrets=secrets_list,
)
class Server:
    @modal.enter()
    def start(self):
        import subprocess

        cmd = [
            "vllm",
            "serve",
            MODEL_NAME,
            "--served-model-name",
            SERVED_MODEL_NAME,
            "nabin2004/AOS-qwen3-8b-grpo-merged",
            "aos-qwen3-8b-grpo",
            "aos-qwen-coder",
            "--host",
            "0.0.0.0",
            "--port",
            str(VLLM_PORT),
            "--uvicorn-log-level=info",
            "--dtype",
            "bfloat16",
            "--max-model-len",
            "32768",
            "--tensor-parallel-size",
            str(N_GPU),
            "--enable-auto-tool-choice",
            "--tool-call-parser",
            "hermes",
        ]

        cmd += ["--enforce-eager" if FAST_BOOT else "--no-enforce-eager"]

        print(*cmd)
        self.process = subprocess.Popen(cmd)

    @modal.exit()
    def stop(self):
        self.process.terminate()


# -----------------------------------------------------------------------
# Local smoke test: `modal run aos_deploy.py`
# -----------------------------------------------------------------------
@app.local_entrypoint()
async def test(test_timeout: int = 15 * MINUTES):
    import asyncio
    import time

    url = await Server.get_url.aio()

    messages = [
        {"role": "system", "content": "You are a helpful coding assistant that writes Manim scenes."},
        {"role": "user", "content": "Write a Manim scene that draws a rotating square."},
    ]

    async with aiohttp.ClientSession(base_url=url) as session:
        print(f"Health-checking {url} ...")
        deadline = time.time() + test_timeout - 1 * MINUTES
        while time.time() < deadline:
            async with session.get("/health", timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    break
                if resp.status == 503:
                    await asyncio.sleep(1)
                    continue
                assert False, f"Health check failed: HTTP {resp.status}"
        else:
            assert False, "Server never became healthy"
        print("Server is healthy. Sending a test chat completion...\n")

        payload: dict[str, Any] = {
            "messages": messages,
            "model": SERVED_MODEL_NAME,
            "stream": True,
        }
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}

        async with session.post("/v1/chat/completions", json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for raw in resp.content:
                line = raw.decode().strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    line = line[len("data: ") :]
                chunk = json.loads(line)
                delta = chunk["choices"][0]["delta"]
                content = delta.get("content")
                if content:
                    print(content, end="", flush=True)
        print()
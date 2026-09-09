#!/usr/bin/env python3
"""Modal serverless deployment for AOS Qwen3-8B Narrated SFT via vLLM.

Features:
- Scales to zero when idle (default 10-min scaledown window) to save costs.
- Persistent HF cache volume to avoid re-downloading 16GB weights on container starts.
- Native /health endpoint: container explicitly waits for vLLM CUDA engine initialization
  to complete before reporting healthy (HTTP 200) and accepting client traffic.
- Full OpenAI-compatible streaming API (/v1/chat/completions, /v1/models).

Deploy:
    modal deploy apps/qwenCoder/modal_vllm_server.py

Test locally / interactively:
    modal serve apps/qwenCoder/modal_vllm_server.py
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any

import modal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
APP_NAME = "aosqwen-server"
DEFAULT_MODEL_REPO = "nabin2004/AOS-qwen3-8b-narrated-sft-merged"
SERVED_MODEL_NAME = "aos-qwen3-8b-narrated-sft"
GPU_TYPE = modal.gpu.A10G()  # Or modal.gpu.L4(), modal.gpu.A100()
VLLM_PORT = 8000
INTERNAL_HOST = "127.0.0.1"
SCALEDOWN_WINDOW_S = 600  # 10 minutes idle before scaling to zero
MAX_MODEL_LEN = 16384
GPU_MEMORY_UTILIZATION = 0.92

# ---------------------------------------------------------------------------
# Container Image & Volumes
# ---------------------------------------------------------------------------
hf_cache_vol = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

vllm_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "vllm>=0.8.0",
        "fastapi>=0.115.0",
        "uvicorn>=0.34.0",
        "httpx>=0.28.0",
        "huggingface_hub>=0.29.0",
    )
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "0",
            "HF_HOME": "/cache/huggingface",
        }
    )
)

app = modal.App(name=APP_NAME, image=vllm_image)


# ---------------------------------------------------------------------------
# Modal Service with Internal Health Verification
# ---------------------------------------------------------------------------
@app.cls(
    gpu=GPU_TYPE,
    scaledown_window=SCALEDOWN_WINDOW_S,
    volumes={"/cache/huggingface": hf_cache_vol},
    secrets=[modal.Secret.from_name("huggingface-secret", required_keys=["HF_TOKEN"])]
    if "HF_TOKEN" in os.environ
    else [],
    timeout=600,
)
class QwenVLLMService:
    @modal.enter()
    def start_vllm(self) -> None:
        """Launch background vLLM process and wait for /health 200 before accepting traffic."""
        import httpx

        model_repo = os.environ.get("MODEL_NAME", DEFAULT_MODEL_REPO)
        served_name = os.environ.get("SERVED_MODEL_NAME", SERVED_MODEL_NAME)

        print(f"🚀 [AOS Modal] Launching vLLM engine for {model_repo} ({served_name})...")
        cmd = [
            "python",
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            model_repo,
            "--served-model-name",
            served_name,
            "--host",
            INTERNAL_HOST,
            "--port",
            str(VLLM_PORT),
            "--gpu-memory-utilization",
            str(GPU_MEMORY_UTILIZATION),
            "--max-model-len",
            str(MAX_MODEL_LEN),
            "--trust-remote-code",
            "--enable-chunked-prefill",
        ]

        self.proc = subprocess.Popen(cmd)
        print(f"⏳ [AOS Modal] vLLM process spawned (PID {self.proc.pid}). Waiting for CUDA initialization...")

        # Poll internal health endpoint until vLLM is fully initialized
        health_url = f"http://{INTERNAL_HOST}:{VLLM_PORT}/health"
        start_wait = time.time()
        timeout_s = 300.0  # 5 minutes max initialization time
        poll_delay = 1.0

        while (time.time() - start_wait) < timeout_s:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"vLLM process exited prematurely with code {self.proc.returncode}"
                )
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(health_url)
                if resp.status_code == 200:
                    elapsed = time.time() - start_wait
                    print(f"✔ [AOS Modal] vLLM is ready and healthy! (took {elapsed:.1f}s)")
                    return
            except Exception:
                pass

            time.sleep(poll_delay)
            poll_delay = min(poll_delay * 1.3, 5.0)

        raise TimeoutError(f"vLLM server failed to become healthy within {timeout_s} seconds")

    @modal.exit()
    def stop_vllm(self) -> None:
        """Clean shutdown of vLLM process on container stop."""
        if hasattr(self, "proc") and self.proc:
            print("🛑 [AOS Modal] Terminating vLLM process...")
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    @modal.asgi_app()
    def app(self) -> Any:
        """FastAPI gateway exposing /health and OpenAI-compatible proxy routes."""
        import httpx
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, StreamingResponse

        api = FastAPI(title="AOS Qwen vLLM Gateway", version="1.0.0")
        target_base = f"http://{INTERNAL_HOST}:{VLLM_PORT}"

        @api.get("/health")
        async def health() -> dict[str, Any]:
            """Explicit health check returning 200 only when vLLM is fully ready."""
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    resp = await client.get(f"{target_base}/health")
                    is_ready = resp.status_code == 200
                except Exception:
                    is_ready = False

            status_code = 200 if is_ready else 503
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": "ok" if is_ready else "initializing",
                    "ready": is_ready,
                    "model": SERVED_MODEL_NAME,
                },
            )

        @api.get("/")
        async def root() -> dict[str, Any]:
            return {
                "service": "AOS Qwen vLLM Server",
                "model": SERVED_MODEL_NAME,
                "endpoints": ["/health", "/v1/models", "/v1/chat/completions"],
            }

        @api.api_route(
            "/v1/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        )
        async def proxy_v1(request: Request, path: str) -> Any:
            """Stream and forward OpenAI requests directly to local vLLM."""
            url = f"{target_base}/v1/{path}"
            headers = dict(request.headers)
            headers.pop("host", None)

            body = await request.body()
            client = httpx.AsyncClient(timeout=300.0)

            # Stream response back to client (essential for SSE chat completions)
            req = client.build_request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                content=body,
            )
            response = await client.send(req, stream=True)

            async def stream_generator():
                try:
                    async for chunk in response.aiter_raw():
                        yield chunk
                finally:
                    await response.aclose()
                    await client.aclose()

            resp_headers = dict(response.headers)
            resp_headers.pop("content-length", None)
            return StreamingResponse(
                stream_generator(),
                status_code=response.status_code,
                headers=resp_headers,
                media_type=response.headers.get("content-type"),
            )

        return api

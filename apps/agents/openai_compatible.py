"""OpenAI-compatible chat model for custom base URLs (vLLM, llama.cpp, Modal)."""

from __future__ import annotations

import json
import logging
import os
import sys
import time

import httpx
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

class RunPodTransport(httpx.AsyncBaseTransport):
    def __init__(self, underlying: httpx.AsyncBaseTransport):
        self._underlying = underlying

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        is_stream = False
        if "runsync" in url_str:
            runsync_idx = url_str.find("/runsync")
            base_runsync_url = url_str[:runsync_idx + len("/runsync")]
            openai_route = url_str[runsync_idx + len("/runsync"):]
            
            if openai_route:
                request.url = httpx.URL(base_runsync_url)
                
                if request.stream:
                    await request.aread()
                    body_bytes = request.content
                    if body_bytes:
                        try:
                            original_json = json.loads(body_bytes)
                            is_stream = original_json.get("stream", False)
                            new_json = {
                                "input": {
                                    "openai_route": openai_route,
                                    "openai_input": original_json
                                }
                            }
                            new_body_bytes = json.dumps(new_json).encode("utf-8")
                            request.stream = httpx.ByteStream(new_body_bytes)
                            request.headers["Content-Length"] = str(len(new_body_bytes))
                        except json.JSONDecodeError:
                            pass
        
        response = await self._underlying.handle_async_request(request)
        
        if "runsync" in url_str and response.status_code == 200:
            await response.aread()
            body_bytes = response.content
            if body_bytes:
                try:
                    resp_json = json.loads(body_bytes)
                    print(f"DEBUG RunPod Response: {resp_json}", file=sys.stderr)
                    if "output" in resp_json:
                        output_data = resp_json["output"]
                        if is_stream:
                            output_data["object"] = "chat.completion.chunk"
                            if "choices" in output_data:
                                for choice in output_data["choices"]:
                                    if "message" in choice:
                                        choice["delta"] = choice.pop("message")
                            sse_payload = f"data: {json.dumps(output_data)}\n\ndata: [DONE]\n\n".encode("utf-8")
                            print(f"DEBUG SSE PAYLOAD: {sse_payload.decode()}", file=sys.stderr)
                            response.stream = httpx.ByteStream(sse_payload)
                            response.headers["Content-Length"] = str(len(sse_payload))
                            response.headers["Content-Type"] = "text/event-stream"
                        else:
                            unwrapped_body = json.dumps(output_data).encode("utf-8")
                            response.stream = httpx.ByteStream(unwrapped_body)
                            response.headers["Content-Length"] = str(len(unwrapped_body))
                    elif "error" in resp_json:
                        error_msg = resp_json.get("error", "Unknown RunPod Error")
                        openai_error = {
                            "error": {
                                "message": str(error_msg),
                                "type": "runpod_error",
                                "param": None,
                                "code": 400
                            }
                        }
                        error_body = json.dumps(openai_error).encode("utf-8")
                        response.status_code = 400
                        response.stream = httpx.ByteStream(error_body)
                        response.headers["Content-Length"] = str(len(error_body))
                        response.headers["Content-Type"] = "application/json"
                except json.JSONDecodeError as e:
                    print(f"DEBUG JSON Decode error: {e}", file=sys.stderr)
                    pass
                    
        return response

_LOCAL_API_KEY_PLACEHOLDER = "local"
_HTTP_TIMEOUT = httpx.Timeout(180.0, connect=30.0)
_OPENAI_MAX_RETRIES = 6
_WARMUP_MAX_WAIT_S = 150.0
_warmup_attempted: set[str] = set()
_warmed_bases: set[str] = set()


def openai_compatible_base_url() -> str | None:
    url = os.getenv("AOS_OPENAI_BASE_URL", "").strip()
    return url or None


def openai_compatible_api_key() -> str:
    key = os.getenv("AOS_OPENAI_API_KEY", "").strip()
    return key or _LOCAL_API_KEY_PLACEHOLDER


def strip_provider_prefix(model: str) -> str:
    for prefix in ("openrouter:", "openai:", "ollama:"):
        if model.startswith(prefix):
            return model[len(prefix) :]
    return model


def models_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/models"
    return f"{base}/v1/models"


def health_urls(base_url: str) -> list[str]:
    """Candidates for waking up and checking custom LLM endpoint readiness."""
    base = base_url.rstrip("/")
    root = base[:-3] if base.endswith("/v1") else base
    urls = [
        f"{root}/health",
        models_url(base_url),
    ]
    if base != root:
        urls.insert(1, f"{base}/health")
    return urls


def warmup_openai_compatible_endpoint(
    base_url: str,
    api_key: str,
    *,
    max_wait_s: float = _WARMUP_MAX_WAIT_S,
) -> bool:
    """Wake scaled-to-zero serverless hosts (Modal) by polling health/models.

    Modal returns HTTP 503 while spinning up GPU containers from zero. We treat
    503 as 'LLM is waking up' rather than 'LLM is broken' and retry until ready.
    """
    key = (base_url or "").rstrip("/")
def warmup_openai_compatible_endpoint(base_url: str, api_key: str, max_wait_s: int = 150):
    """Pings the base_url /models endpoint until it returns a 200."""
    url = f"{base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    start_time = time.time()
    delay = 1.0
    last_err = ""

    while time.time() - start_time < max_wait_s:
        try:
            response = httpx.get(url, headers=headers, timeout=2.0)
            if response.status_code == 200:
                elapsed = time.time() - start_time
                logger.info(
                    "Custom LLM endpoint ready at %s (took %.1fs)", url, elapsed
                )
                return True
            else:
                last_err = f"HTTP {response.status_code}"
                if response.status_code == 503:
                    elapsed = int(time.time() - start_time)
                    logger.info(
                        "Custom LLM endpoint is waking up (HTTP 503) at %s... (%ds elapsed)",
                        url,
                        elapsed,
                    )
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            last_err = str(exc)
            elapsed = int(time.time() - start_time)
            logger.info(
                "Waiting for custom LLM host connection (%s)... (%ds elapsed)",
                url,
                elapsed,
            )
        except httpx.HTTPError as exc:
            last_err = str(exc)

        time.sleep(delay)
        delay = min(delay * 1.5, 6.0)

    logger.warning(
        "Custom LLM warmup did not complete within %.0fs (%s) at %s; proceeding to chat call",
        max_wait_s,
        last_err,
        base_url,
    )
    return False


def build_openai_provider(base_url: str, api_key: str) -> OpenAIProvider:
    """Provider with long timeouts and SDK retries (includes HTTP 503)."""
    if "api.runpod.ai" not in base_url:
        warmup_openai_compatible_endpoint(base_url, api_key)
    
    # Use standard transport, but wrap it in RunPodTransport to intercept and rewrite payloads if hitting runpod
    transport = RunPodTransport(httpx.AsyncHTTPTransport())
    http_client = httpx.AsyncClient(timeout=180.0, transport=transport)
    
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=180.0,
        max_retries=_OPENAI_MAX_RETRIES,
        http_client=http_client,
    )
    return OpenAIProvider(openai_client=client)


def format_custom_endpoint_error(
    error: str | Exception,
    *,
    base_url: str | None = None,
) -> str:
    """Format 503, 401, timeout, and fallback errors into clear, actionable messages."""
    if isinstance(error, BaseException):
        if hasattr(error, "exceptions"):
            subs = [
                format_custom_endpoint_error(sub, base_url=base_url)
                for sub in getattr(error, "exceptions", [])
            ]
            return f"All models failed: {' | '.join(subs)}"
        text = str(error).strip()
    else:
        text = str(error or "").strip()

    if "Custom LLM endpoint is unavailable" in text or "LLM authentication failed" in text:
        return text
    lowered = text.lower()
    if "401" in lowered or "invalid_token" in lowered or "api key expired" in lowered or "unauthorized" in lowered:
        return (
            "LLM authentication failed (HTTP 401: API key expired or invalid). "
            "Please configure a valid OPENROUTER_API_KEY in apps/ui/aos/backend/.env "
            "or set your custom LLM provider in Settings."
        )
    if any(k in lowered for k in ("503", "502", "504", "service unavailable", "connecterror", "connection refused", "timeout")):
        host = (base_url or openai_compatible_base_url() or "the custom LLM endpoint").rstrip("/")
        return (
            f"Custom LLM endpoint is unavailable (HTTP 503) or waking up ({host}). "
            "Serverless containers (Modal) can take 1–2 minutes to scale up from zero and load weights into GPU memory. "
            "The Modal app may be scaled to zero or still loading — wait and retry, "
            "or redeploy nabinoli2004--aos-qwen-coder-server and confirm the UI base URL "
            "ends with /v1. "
            f"Original: {text[:400]}"
        )
    return text or "custom_llm_failed"


def build_openai_compatible_chat_model(model: str) -> OpenAIChatModel:
    """OpenAIChatModel pointed at AOS_OPENAI_BASE_URL (key optional / placeholder)."""
    base = openai_compatible_base_url()
    if not base:
        raise RuntimeError("AOS_OPENAI_BASE_URL is required to build an OpenAI-compatible model")
    name = strip_provider_prefix(model)
    return OpenAIChatModel(
        name,
        provider=build_openai_provider(base, openai_compatible_api_key()),
    )

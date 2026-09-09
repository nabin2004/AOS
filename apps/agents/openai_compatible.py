"""OpenAI-compatible chat model for custom base URLs (vLLM, llama.cpp, Modal)."""

from __future__ import annotations

import logging
import os
import time

import httpx
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

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
    if not key or key in _warmed_bases:
        return True

    urls = health_urls(base_url)
    headers: dict[str, str] = {}
    if api_key and api_key != _LOCAL_API_KEY_PLACEHOLDER:
        headers["Authorization"] = f"Bearer {api_key}"

    start_time = time.time()
    delay = 1.0
    last_err = "unknown"

    while (time.time() - start_time) < max_wait_s:
        for url in urls:
            try:
                with httpx.Client(timeout=httpx.Timeout(15.0, connect=10.0)) as client:
                    response = client.get(url, headers=headers)
                if response.status_code == 200:
                    _warmed_bases.add(key)
                    elapsed = time.time() - start_time
                    logger.info("Custom LLM endpoint ready (%s, took %.1fs)", url, elapsed)
                    return True
                if response.status_code in {401, 403, 404}:
                    # Host is active; authentication or endpoint route may differ
                    _warmed_bases.add(key)
                    return True
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
    warmup_openai_compatible_endpoint(base_url, api_key)
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=180.0,
        max_retries=_OPENAI_MAX_RETRIES,
    )
    try:
        return OpenAIProvider(openai_client=client)
    except TypeError:
        http_client = httpx.AsyncClient(timeout=_HTTP_TIMEOUT)
        return OpenAIProvider(
            base_url=base_url,
            api_key=api_key,
            http_client=http_client,
        )


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

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
_OPENAI_MAX_RETRIES = 4
_WARMUP_BACKOFF_S = (0.0, 2.0, 5.0, 15.0)
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


def warmup_openai_compatible_endpoint(base_url: str, api_key: str) -> None:
    """GET /v1/models to wake scaled-to-zero hosts (Modal). Best-effort."""
    key = (base_url or "").rstrip("/")
    if not key or key in _warmup_attempted:
        return
    _warmup_attempted.add(key)
    url = models_url(base_url)
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    last_err = "unknown"
    for delay in _WARMUP_BACKOFF_S:
        if delay:
            time.sleep(delay)
        try:
            with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
                response = client.get(url, headers=headers)
            if response.status_code == 200:
                _warmed_bases.add(key)
                logger.info("Custom LLM endpoint ready: %s", url)
                return
            if response.status_code in {401, 403, 404}:
                # Server is up; auth/path may still allow chat completions.
                _warmed_bases.add(key)
                return
            last_err = f"HTTP {response.status_code}"
            if response.status_code not in {429, 502, 503, 504}:
                break
            logger.warning("Custom LLM warmup %s (%s); retrying", url, last_err)
        except httpx.HTTPError as exc:
            last_err = str(exc)
            logger.warning("Custom LLM warmup error %s: %s", url, exc)
    logger.warning(
        "Custom LLM warmup did not succeed (%s) at %s; chat calls will retry",
        last_err,
        url,
    )


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


def format_custom_endpoint_error(error: str, *, base_url: str | None = None) -> str:
    """Format 503 and 401 errors into clear, actionable messages."""
    text = (error or "").strip()
    if "Custom LLM endpoint is unavailable" in text or "LLM authentication failed" in text:
        return text
    lowered = text.lower()
    if "401" in lowered or "invalid_token" in lowered or "api key expired" in lowered or "unauthorized" in lowered:
        return (
            "LLM authentication failed (HTTP 401: API key expired or invalid). "
            "Please configure a valid OPENROUTER_API_KEY in apps/ui/aos/backend/.env "
            "or set your custom LLM provider in Settings."
        )
    if "503" not in lowered and "service unavailable" not in lowered:
        return text or "custom_llm_failed"
    host = (base_url or openai_compatible_base_url() or "the custom LLM endpoint").rstrip("/")
    return (
        "Custom LLM endpoint is unavailable (HTTP 503). "
        "The Modal app may be scaled to zero or still loading — wait and retry, "
        "or redeploy nabinoli2004--aos-qwen-coder-server and confirm the UI base URL "
        f"ends with /v1 ({host}). "
        f"Original: {text[:400]}"
    )


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

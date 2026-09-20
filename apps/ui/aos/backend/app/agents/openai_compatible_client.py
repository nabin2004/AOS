"""OpenAI-compatible HTTP client for BYOK / Modal (long timeout + 503 retries)."""

from __future__ import annotations

import asyncio
import logging

import httpx
from openai import AsyncOpenAI
from pydantic_ai.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

LOCAL_API_KEY_PLACEHOLDER = "local"
HTTP_TIMEOUT = httpx.Timeout(180.0, connect=30.0)
OPENAI_MAX_RETRIES = 6
WARMUP_MAX_WAIT_S = 150.0
_warmup_attempted: set[str] = set()
_warmed_bases: set[str] = set()


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
    if any(k in lowered for k in ("401", "invalid_token", "api key expired", "unauthorized")):
        return (
            "LLM authentication failed (HTTP 401: API key expired or invalid). "
            "Please configure a valid OPENROUTER_API_KEY in apps/ui/aos/backend/.env "
            "or set your custom LLM provider in Settings."
        )
    if any(k in lowered for k in (
        "connection error",
        "connecterror",
        "connection refused",
        "failed to connect",
        "cannot connect",
        "apiconnectionerror",
        "network unreachable",
        "name resolution",
        "dns",
        "getaddrinfo failed",
        "all connection attempts failed",
    )):
        host = (base_url or "the custom LLM endpoint").rstrip("/")
        return (
            f"Cannot connect to LLM endpoint ({host}). "
            "Please verify that your custom LLM provider (Ollama, HuggingFace endpoint, Modal, or local server) "
            f"is running and accessible, and verify the Base URL in Chat Settings ({host}) ends with /v1 if required. "
            f"[Raw error: {text[:200]}]"
        )
    if any(k in lowered for k in ("503", "502", "504", "service unavailable", "timeout", "timed out")):
        host = (base_url or "the custom LLM endpoint").rstrip("/")
        return (
            f"Custom LLM endpoint is unavailable (HTTP 503) or timed out ({host}). "
            "Serverless containers (Modal / HuggingFace Spaces) can take 1–2 minutes to scale up from zero and load weights into GPU memory. "
            "Please wait and retry in a moment. "
            f"Original: {text[:400]}"
        )
    return text or "custom_llm_failed"


def diagnose_endpoint_error(
    error: str | Exception,
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Generate structured diagnostic metadata for frontend and telemetry."""
    err_text = str(error).strip() if error else "Unknown error"
    lowered = err_text.lower()
    host = (base_url or "").rstrip("/")

    err_type = "APIConnectionError" if any(k in lowered for k in ("connection", "connect", "dns", "getaddrinfo")) else type(error).__name__
    if "401" in lowered or "unauthorized" in lowered:
        category = "auth"
        hint = "Check your API key in Settings or backend .env."
    elif any(k in lowered for k in ("connection error", "connecterror", "connection refused", "getaddrinfo", "dns")):
        category = "connection_refused"
        hint = f"Cannot reach endpoint '{host}'. Confirm the service is running and accessible."
    elif any(k in lowered for k in ("503", "502", "504", "timeout", "timed out")):
        category = "service_unavailable"
        hint = f"Server at '{host}' is overloaded, waking up, or timed out."
    else:
        category = "general_error"
        hint = "Review backend logs for complete traceback."

    return {
        "error_type": err_type,
        "category": category,
        "message": format_custom_endpoint_error(error, base_url=base_url),
        "raw_error": err_text,
        "endpoint": host or "default_openrouter",
        "model": model or "unknown",
        "hint": hint,
    }



async def warmup_openai_compatible_endpoint_async(
    base_url: str,
    api_key: str,
    *,
    max_wait_s: float = WARMUP_MAX_WAIT_S,
) -> bool:
    key = (base_url or "").rstrip("/")
    if not key or key in _warmed_bases:
        return True

    urls = health_urls(base_url)
    headers: dict[str, str] = {}
    if api_key and api_key != LOCAL_API_KEY_PLACEHOLDER:
        headers["Authorization"] = f"Bearer {api_key}"

    start_time = asyncio.get_event_loop().time()
    delay = 1.0
    last_err = "unknown"

    while (asyncio.get_event_loop().time() - start_time) < max_wait_s:
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=10.0)) as client:
                    response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    _warmed_bases.add(key)
                    elapsed = asyncio.get_event_loop().time() - start_time
                    logger.info("Custom LLM endpoint ready (%s, took %.1fs)", url, elapsed)
                    return True
                if response.status_code in {401, 403, 404}:
                    _warmed_bases.add(key)
                    return True
                last_err = f"HTTP {response.status_code}"
                if response.status_code == 503:
                    elapsed = int(asyncio.get_event_loop().time() - start_time)
                    logger.info(
                        "Custom LLM endpoint is waking up (HTTP 503) at %s... (%ds elapsed)",
                        url,
                        elapsed,
                    )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                last_err = str(exc)
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                logger.info(
                    "Waiting for custom LLM host connection (%s)... (%ds elapsed)",
                    url,
                    elapsed,
                )
            except httpx.HTTPError as exc:
                last_err = str(exc)

        await asyncio.sleep(delay)
        delay = min(delay * 1.5, 6.0)

    logger.warning(
        "Custom LLM warmup did not complete within %.0fs (%s) at %s; proceeding to chat call",
        max_wait_s,
        last_err,
        base_url,
    )
    return False


def warmup_openai_compatible_endpoint(base_url: str, api_key: str) -> None:
    """Sync warmup for non-async callers (tests / scripts)."""
    asyncio.run(warmup_openai_compatible_endpoint_async(base_url, api_key))


def build_openai_provider(base_url: str, api_key: str) -> OpenAIProvider:
    """Provider with ~180s timeout and SDK retries (covers HTTP 503)."""
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=180.0,
        max_retries=OPENAI_MAX_RETRIES,
    )
    try:
        return OpenAIProvider(openai_client=client)
    except TypeError:
        http_client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        return OpenAIProvider(
            base_url=base_url,
            api_key=api_key,
            http_client=http_client,
        )

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
OPENAI_MAX_RETRIES = 4
WARMUP_BACKOFF_S = (0.0, 2.0, 5.0, 15.0)
_warmup_attempted: set[str] = set()
_warmed_bases: set[str] = set()


def models_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/models"
    return f"{base}/v1/models"


def format_custom_endpoint_error(error: str, *, base_url: str | None = None) -> str:
    """Replace empty 503 bodies with an actionable message."""
    text = (error or "").strip()
    if "Custom LLM endpoint is unavailable" in text:
        return text
    lowered = text.lower()
    if "503" not in lowered and "service unavailable" not in lowered:
        return text or "custom_llm_failed"
    host = (base_url or "the custom LLM endpoint").rstrip("/")
    return (
        "Custom LLM endpoint is unavailable (HTTP 503). "
        "The Modal app may be scaled to zero or still loading — wait and retry, "
        "or redeploy nabinoli2004--aos-qwen-coder-server and confirm the UI base URL "
        f"ends with /v1 ({host}). "
        f"Original: {text[:400]}"
    )


async def warmup_openai_compatible_endpoint_async(base_url: str, api_key: str) -> None:
    key = (base_url or "").rstrip("/")
    if not key or key in _warmup_attempted:
        return
    _warmup_attempted.add(key)
    url = models_url(base_url)
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    last_err = "unknown"
    for delay in WARMUP_BACKOFF_S:
        if delay:
            await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.get(url, headers=headers)
            if response.status_code == 200:
                _warmed_bases.add(key)
                logger.info("Custom LLM endpoint ready: %s", url)
                return
            if response.status_code in {401, 403, 404}:
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

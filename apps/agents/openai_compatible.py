"""OpenAI-compatible chat model for custom base URLs (vLLM, llama.cpp, local proxies)."""

from __future__ import annotations

import os

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

_LOCAL_API_KEY_PLACEHOLDER = "local"


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


def build_openai_compatible_chat_model(model: str) -> OpenAIChatModel:
    """OpenAIChatModel pointed at AOS_OPENAI_BASE_URL (key optional / placeholder)."""
    base = openai_compatible_base_url()
    if not base:
        raise RuntimeError("AOS_OPENAI_BASE_URL is required to build an OpenAI-compatible model")
    name = strip_provider_prefix(model)
    return OpenAIChatModel(
        name,
        provider=OpenAIProvider(
            base_url=base,
            api_key=openai_compatible_api_key(),
        ),
    )

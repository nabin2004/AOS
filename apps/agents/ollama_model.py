"""Ollama model wiring: disable thinking to save context on multi-turn CodeMode runs."""

from __future__ import annotations

import os

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles import merge_profile
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.settings import ModelSettings


def ollama_thinking_enabled() -> bool:
    """Default off — Gemma thinking/reasoning bloats ctx on tool-call retries."""
    value = os.getenv("AOS_OLLAMA_THINKING", "0").strip().lower()
    return value in ("1", "true", "yes", "on")


def strip_ollama_prefix(model: str) -> str:
    if model.startswith("ollama:"):
        return model[len("ollama:") :]
    return model


def ollama_extra_body(*, num_ctx: int) -> dict[str, object]:
    body: dict[str, object] = {"options": {"num_ctx": num_ctx}}
    if not ollama_thinking_enabled():
        body["think"] = False
        body["chat_template_kwargs"] = {"enable_thinking": False}
    return body


def ollama_model_settings(*, max_tokens: int, num_ctx: int) -> ModelSettings:
    settings: ModelSettings = {
        "max_tokens": max_tokens,
        "extra_body": ollama_extra_body(num_ctx=num_ctx),
    }
    if not ollama_thinking_enabled():
        settings["thinking"] = False
    return settings


def build_ollama_chat_model(model: str) -> OpenAIChatModel:
    """OpenAIChatModel with reasoning not echoed back into later turns."""
    name = strip_ollama_prefix(model)
    base = OpenAIChatModel(name, provider="ollama")
    if ollama_thinking_enabled():
        return base
    return OpenAIChatModel(
        name,
        provider="ollama",
        profile=merge_profile(
            base.profile,
            OpenAIModelProfile(openai_chat_send_back_thinking_parts=False),
        ),
    )


def resolve_model(model: str) -> str | OpenAIChatModel:
    """Model string for cloud providers; patched OpenAIChatModel for Ollama."""
    if model.startswith("ollama:"):
        return build_ollama_chat_model(model)
    return model

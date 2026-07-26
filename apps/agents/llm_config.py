"""Central LLM model selection for the Manim animation pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from pydantic_ai.settings import ModelSettings

from ollama_model import ollama_extra_body, ollama_thinking_enabled, resolve_model

TRAINING_ROOT = Path(__file__).resolve().parents[1] / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from model_identity import OLLAMA_HF_GGUF_REF  # noqa: E402

AgentRole = Literal["classifier", "planner", "coder", "animation"]

_PIPELINE_ROLES: tuple[AgentRole, ...] = ("classifier", "planner", "coder", "animation")

_DEFAULT_OLLAMA = f"ollama:{OLLAMA_HF_GGUF_REF}"
_DEFAULT_OPENROUTER = "openrouter:openai/gpt-4o-mini"

_PROFILES: dict[str, dict[AgentRole, str]] = {
    "hybrid": {
        "classifier": _DEFAULT_OPENROUTER,
        "planner": _DEFAULT_OPENROUTER,
        "animation": _DEFAULT_OPENROUTER,
        "coder": _DEFAULT_OLLAMA,
    },
    "local": {
        "classifier": _DEFAULT_OLLAMA,
        "planner": _DEFAULT_OLLAMA,
        "animation": _DEFAULT_OLLAMA,
        "coder": _DEFAULT_OLLAMA,
    },
    "cloud": {
        "classifier": _DEFAULT_OPENROUTER,
        "planner": _DEFAULT_OPENROUTER,
        "animation": _DEFAULT_OPENROUTER,
        "coder": _DEFAULT_OPENROUTER,
    },
}

_ROLE_ENV: dict[AgentRole, str] = {
    "classifier": "AOS_CLASSIFIER_MODEL",
    "planner": "AOS_PLANNER_MODEL",
    "coder": "AOS_CODER_MODEL",
    "animation": "AOS_ANIMATION_MODEL",
}


def _env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value or default


def profile_name() -> str:
    profile = _env("AOS_MODEL_PROFILE", "hybrid").lower()
    if profile not in _PROFILES:
        return "hybrid"
    return profile


def _ollama_model() -> str:
    return _env("AOS_OLLAMA_MODEL", _DEFAULT_OLLAMA)


def _openrouter_model() -> str:
    return _env("AOS_OPENROUTER_MODEL", _DEFAULT_OPENROUTER)


def _resolve_profile_model(role: AgentRole) -> str:
    profile = profile_name()
    models = _PROFILES[profile].copy()
    if profile == "local":
        ollama = _ollama_model()
        return ollama
    if profile == "cloud":
        openrouter = _openrouter_model()
        return openrouter
    # hybrid: substitute env-tuned defaults for ollama/openrouter slots
    models["coder"] = _ollama_model()
    for r in ("classifier", "planner", "animation"):
        models[r] = _openrouter_model()
    return models[role]


def is_ollama(model: str) -> bool:
    return model.startswith("ollama:")


def model_for(role: AgentRole) -> str:
    override = os.getenv(_ROLE_ENV[role], "").strip()
    if override:
        return override
    return _resolve_profile_model(role)


def _max_tokens_for(role: AgentRole) -> int:
    if role == "coder":
        return int(_env("AOS_CODER_MAX_TOKENS", "2048"))
    return int(_env("AOS_MAX_TOKENS", "2048"))


def _ollama_num_ctx() -> int:
    return int(_env("AOS_OLLAMA_NUM_CTX", "16384"))


def settings_for(role: AgentRole) -> ModelSettings | None:
    model = model_for(role)
    if not is_ollama(model):
        return None
    settings: ModelSettings = {
        "max_tokens": _max_tokens_for(role),
        "extra_body": ollama_extra_body(num_ctx=_ollama_num_ctx()),
    }
    if not ollama_thinking_enabled():
        settings["thinking"] = False
    return settings


def model_for_agent(role: AgentRole) -> str | object:
    """Resolved model for Agent(...): patched Ollama chat model when local."""
    return resolve_model(model_for(role))


def resolved_models() -> dict[str, str]:
    """Return active profile and resolved model string per pipeline role."""
    return {role: model_for(role) for role in _PIPELINE_ROLES}


class PipelineEnvError(RuntimeError):
    """Missing or invalid environment for the animation pipeline."""


def validate_pipeline_env() -> dict[str, str]:
    """Fail fast if required API keys / endpoints are missing for active models."""
    models = resolved_models()
    profile = profile_name()
    errors: list[str] = []

    needs_openrouter = any(not is_ollama(m) for m in models.values())
    needs_ollama = any(is_ollama(m) for m in models.values())

    if needs_openrouter and not os.getenv("OPENROUTER_API_KEY", "").strip():
        errors.append(
            "OPENROUTER_API_KEY is required (profile uses OpenRouter models). "
            "Set it in apps/agents/.env"
        )

    if needs_ollama and not os.getenv("OLLAMA_BASE_URL", "").strip():
        errors.append(
            "OLLAMA_BASE_URL is required (profile uses Ollama models). "
            "Example: export OLLAMA_BASE_URL=http://localhost:11434/v1"
        )

    if errors:
        detail = "\n".join(f"  - {e}" for e in errors)
        raise PipelineEnvError(
            f"Animation pipeline preflight failed (profile={profile}):\n{detail}"
        )

    return {"profile": profile, **models}

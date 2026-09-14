"""Factory and registry for instantiating the configured Visual Critic."""

from __future__ import annotations

import os
from typing import Optional

from .base import BaseVisualCritic
from .heuristic import HeuristicVisionCritic
from .hybrid import HybridVisionCritic
from .moondream import MoondreamCritic
from .ollama import OllamaVisionCritic
from .openrouter import OpenRouterVisionCritic


def get_visual_critic(
    backend: Optional[str] = None,
    model: Optional[str] = None,
    pass_threshold: Optional[float] = None,
    device: Optional[str] = None,
) -> BaseVisualCritic:
    """Instantiates the visual critic based on explicit parameters or environment configuration.

    Environment variables:
        AOS_VISUAL_CRITIC_BACKEND: moondream | openrouter | ollama | hybrid | heuristic | auto
        AOS_VISUAL_CRITIC_MODEL: Model identifier (e.g. vikhyatk/moondream-0_5b, google/gemini-2.5-flash)
        AOS_VISUAL_CRITIC_PASS_THRESHOLD: Minimum passing score (default 0.70)
        AOS_VISUAL_CRITIC_DEVICE: cuda | cpu | auto (default auto)
        EDUCLAW_VISION_MODEL: Legacy fallback model identifier
    """
    effective_backend = (
        backend
        or os.getenv("AOS_VISUAL_CRITIC_BACKEND")
        or "moondream"
    ).lower().strip()

    threshold = float(
        pass_threshold
        or os.getenv("AOS_VISUAL_CRITIC_PASS_THRESHOLD")
        or "0.70"
    )

    dev = device or os.getenv("AOS_VISUAL_CRITIC_DEVICE", "auto")

    # Resolve model override if provided
    raw_model = (
        model
        or os.getenv("AOS_VISUAL_CRITIC_MODEL")
        or os.getenv("EDUCLAW_VISION_MODEL")
        or ""
    ).strip()

    # Automatic provider resolution
    if effective_backend == "auto":
        has_openrouter = bool(
            os.getenv("OPENROUTER_API_KEY")
            or os.getenv("AOS_OPENROUTER_API_KEY")
        )
        has_ollama = bool(os.getenv("OLLAMA_BASE_URL"))

        if has_openrouter:
            # If OpenRouter is available, default to Hybrid (Moondream 0.5B + Gemini Flash escalation)
            # or direct OpenRouter if explicit
            if "gemini" in raw_model.lower() or "gpt" in raw_model.lower():
                effective_backend = "openrouter"
            else:
                effective_backend = "hybrid"
        elif has_ollama:
            effective_backend = "ollama"
        else:
            effective_backend = "moondream"

    # Backend: Moondream (0.5B default, easily replaced with 2B or custom checkpoint)
    if effective_backend in ("moondream", "moondream_local", "moondream_0.5b", "moondream-0.5b", "moondream2"):
        m_name = raw_model or os.getenv("AOS_VISUAL_CRITIC_MODEL") or "vikhyatk/moondream-0_5b"
        use_ollama = bool(os.getenv("AOS_MOONDREAM_USE_OLLAMA", "0") == "1")
        return MoondreamCritic(model_name=m_name, device=dev, pass_threshold=threshold, use_ollama=use_ollama)

    # Backend: Hybrid (Moondream front-line filter + Gemini Flash escalation)
    if effective_backend == "hybrid":
        m_moondream = "vikhyatk/moondream-0_5b"
        m_escalation = raw_model or "google/gemini-2.5-flash"
        return HybridVisionCritic(
            moondream_model=m_moondream,
            escalation_model=m_escalation,
            pass_threshold=threshold,
        )

    # Backend: OpenRouter (Google Gemini Flash / Pro / GPT-4o)
    if effective_backend in ("openrouter", "gemini", "gemini_flash", "cloud"):
        m_name = raw_model or "google/gemini-2.5-flash"
        return OpenRouterVisionCritic(model_name=m_name, pass_threshold=threshold)

    # Backend: Ollama (moondream, qwen2.5-vl, minicpm-v)
    if effective_backend == "ollama":
        m_name = raw_model or "moondream"
        return OllamaVisionCritic(model_name=m_name, pass_threshold=threshold)

    # Backend: Heuristic (pixel statistics, edge density, zero dependencies)
    if effective_backend in ("heuristic", "mock", "test"):
        return HeuristicVisionCritic(pass_threshold=threshold)

    # Default fallback
    return MoondreamCritic(
        model_name=raw_model or "vikhyatk/moondream-0_5b",
        device=dev,
        pass_threshold=threshold,
    )

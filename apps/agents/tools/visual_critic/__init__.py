"""AOS Visual Critic Subsystem.

Provides modular visual quality control and automated code repair for Manim animation slides:
- Moondream 0.5B / 2B targeted visual interrogation (10 constrained checks).
- OpenRouter / Google Gemini 2.5 Flash frontier multimodal analysis.
- Ollama vision models (moondream, qwen2.5-vl).
- Multi-layer Hybrid evaluation (Moondream filter + Gemini Flash escalation).
- Zero-dependency Heuristic frame safety net.
"""

from .base import BaseVisualCritic
from .factory import get_visual_critic
from .heuristic import HeuristicVisionCritic
from .hybrid import HybridVisionCritic
from .moondream import MoondreamCritic
from .ollama import OllamaVisionCritic
from .openrouter import OpenRouterVisionCritic
from .types import (
    TARGETED_VISUAL_QUESTIONS,
    VisualCheckItem,
    VisualContext,
    VisualCriticVerdict,
    VisualQuestionDef,
)

__all__ = [
    "BaseVisualCritic",
    "HeuristicVisionCritic",
    "HybridVisionCritic",
    "MoondreamCritic",
    "OllamaVisionCritic",
    "OpenRouterVisionCritic",
    "TARGETED_VISUAL_QUESTIONS",
    "VisualCheckItem",
    "VisualContext",
    "VisualCriticVerdict",
    "VisualQuestionDef",
    "get_visual_critic",
]

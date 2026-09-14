"""Comprehensive test suite for the 10 Presentation Prompts & Pipeline Robustness.

Tests multi-model failover, 503 capacity resilience, Moondream graceful degradation,
and end-to-end curriculum generation across 10 diverse STEM presentation topics.
"""

from pathlib import Path
import pytest
import sys
from unittest.mock import MagicMock, patch

# Ensure apps/agents is importable
repo_root = Path(__file__).resolve().parents[1]
agents_dir = repo_root / "apps" / "agents"
if str(agents_dir) not in sys.path:
    sys.path.insert(0, str(agents_dir))

from apps.agents.keyframe_engine import (
    _extract_topic_title,
    _build_curated_fallback_segment,
    plan_teaching_segment,
    execute_completion_with_fallback,
)
from apps.agents.tools.visual_critic.moondream import MoondreamCritic
from apps.agents.tools.visual_critic.heuristic import HeuristicVisionCritic
from apps.agents.tools.visual_critic.types import VisualContext
from apps.agents.error_classifier import classify_error, ErrorCategory


# The 10 Curated Presentation Prompts across Mathematics, Physics, and Computer Science
PRESENTATION_PROMPTS = [
    ("Euler's Formula", "Teach me about Euler's formula"),
    ("BODMAS Rule", "Teach me about the BODMAS rule and order of operations"),
    ("Fourier Transform", "Explain the Fourier Transform and frequency decomposition"),
    ("Pythagorean Theorem", "Visualize the Pythagorean theorem with geometric proof"),
    ("Newton's Second Law", "Teach me about Newton's second law of motion F = ma"),
    ("Binary Search Algorithm", "Explain the Binary Search algorithm visually"),
    ("Bayes' Theorem", "Explain Bayes' Theorem and conditional probability"),
    ("Universal Gravitation", "Visualize Newton's law of universal gravitation and orbital paths"),
    ("Neural Network Forward Pass", "Explain how a neural network forward pass works"),
    ("Matrix Multiplication", "Show me how 2x2 matrix multiplication transforms 2D space"),
]


@pytest.mark.parametrize("concept_name,prompt", PRESENTATION_PROMPTS)
def test_presentation_prompt_title_extraction(concept_name: str, prompt: str):
    """Verify that all 10 presentation prompts are cleanly condensed into professional titles."""
    extracted = _extract_topic_title(prompt)
    assert len(extracted) > 0
    assert len(extracted) <= 70
    assert not extracted.lower().startswith("teach me about")
    assert not extracted.lower().startswith("explain")


@pytest.mark.parametrize("concept_name,prompt", PRESENTATION_PROMPTS)
def test_presentation_prompt_fallback_segment_generation(concept_name: str, prompt: str):
    """Verify that every presentation prompt generates a complete, non-empty visual anchor and code."""
    for slide_num in (1, 2, 3):
        segment = _build_curated_fallback_segment(prompt, slide_num=slide_num, total_slides=3)
        assert segment.slide_num == slide_num
        assert len(segment.concept) > 0
        assert segment.visual_anchor is not None
        assert len(segment.visual_anchor.title) > 0
        assert len(segment.visual_anchor.key_definitions) > 0
        assert len(segment.manim_code.strip()) > 0
        assert len(segment.narration.split()) >= 15


def test_execute_completion_with_fallback_on_503():
    """Verify that execute_completion_with_fallback transparently switches models on 503 UNAVAILABLE."""
    mock_client = MagicMock()
    mock_client.base_url = "https://openrouter.ai/api/v1"

    # Simulate Gemini failing with 503 capacity error on first attempt, then gpt-4o-mini succeeding
    gemini_error = Exception("Error: UNAVAILABLE (code 503): No capacity available for model gemini-3.8-flash-medium")
    success_resp = MagicMock()
    success_resp.choices = [MagicMock(message=MagicMock(content="Success from fallback model"))]

    mock_client.chat.completions.create.side_effect = [gemini_error, success_resp]

    result = execute_completion_with_fallback(
        client=mock_client,
        primary_model="google/gemini-2.5-flash",
        messages=[{"role": "user", "content": "Test prompt"}],
    )

    assert result.choices[0].message.content == "Success from fallback model"
    assert mock_client.chat.completions.create.call_count == 2
    # First call was Gemini
    assert mock_client.chat.completions.create.call_args_list[0].kwargs["model"] == "google/gemini-2.5-flash"
    # Second call was gpt-4o-mini
    assert mock_client.chat.completions.create.call_args_list[1].kwargs["model"] == "openai/gpt-4o-mini"


def test_moondream_graceful_heuristic_fallback(tmp_path: Path):
    """Verify that Moondream immediately delegates to HeuristicVisionCritic when model loading fails."""
    critic = MoondreamCritic(model_name="vikhyatk/nonexistent_model")

    # Create dummy black and valid image files
    from PIL import Image
    test_img_path = tmp_path / "test_frame.png"
    img = Image.new("RGB", (480, 270), color=(15, 23, 42))
    img.save(test_img_path)

    v_ctx = VisualContext(
        slide_num=1,
        concept="Euler's Formula",
        learning_objective="Visual verification",
        latex_formula=r"e^{i\pi} + 1 = 0",
        visible_elements=["e", "pi"],
        key_definitions=["Identity"],
        manim_code="self.play(Write(formula))",
    )

    verdict = critic.critique_frame(test_img_path, v_ctx)
    assert verdict is not None
    assert critic._model_load_failed is True
    # The checks were produced by HeuristicVisionCritic
    assert verdict.backend in ("heuristic", "moondream")
    assert len(verdict.checks) > 0


def test_error_classifier_recognizes_503_capacity_exhaustion():
    """Verify error classifier tags 503 capacity errors as TRANSIENT_LLM_ERROR with retryable=True."""
    raw_error = "Error: UNAVAILABLE (code 503): No capacity available for model gemini-3.8-flash-medium on the server"
    classified = classify_error(raw_error)

    assert classified.category == ErrorCategory.TRANSIENT_LLM_ERROR
    assert classified.is_retryable is True
    assert "capacity" in classified.user_message.lower() or "503" in classified.user_message

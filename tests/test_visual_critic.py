"""Tests for Moondream 0.5B / Multi-Model Visual Critic and Retry Loop Architecture."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "agents"))

from tools.visual_critic import (
    BaseVisualCritic,
    HeuristicVisionCritic,
    HybridVisionCritic,
    MoondreamCritic,
    OllamaVisionCritic,
    OpenRouterVisionCritic,
    TARGETED_VISUAL_QUESTIONS,
    VisualCheckItem,
    VisualContext,
    VisualCriticVerdict,
    get_visual_critic,
)


@pytest.fixture
def black_frame(tmp_path: Path) -> Path:
    """Creates a 854x480 completely pitch black image."""
    img_path = tmp_path / "black_frame.png"
    arr = np.zeros((480, 854, 3), dtype=np.uint8)
    Image.fromarray(arr).save(img_path)
    return img_path


@pytest.fixture
def valid_slide_frame(tmp_path: Path) -> Path:
    """Creates a synthetic slide image with title, formula, and text."""
    img_path = tmp_path / "valid_slide.png"
    arr = np.zeros((480, 854, 3), dtype=np.uint8)
    # Add title (yellow band)
    arr[40:70, 200:654] = [255, 215, 0]
    # Add formula box (blue and gold)
    arr[120:180, 150:700] = [30, 144, 255]
    # Add bullet breakdown
    arr[220:240, 100:600] = [255, 255, 255]
    arr[260:280, 100:550] = [255, 255, 255]
    arr[300:320, 100:580] = [255, 255, 255]
    Image.fromarray(arr).save(img_path)
    return img_path


def test_10_targeted_visual_questions_structure():
    """Verify all 10 constrained visual questions are properly defined with penalties and fixes."""
    assert len(TARGETED_VISUAL_QUESTIONS) == 10
    ids = [q.id for q in TARGETED_VISUAL_QUESTIONS]
    expected_ids = [
        "scene_empty",
        "equation_visible",
        "equation_cutoff",
        "objects_overlapping",
        "text_too_small",
        "excessive_empty_space",
        "diagram_appeared",
        "stuck_frame",
        "labels_readable",
        "layout_coherent",
    ]
    assert ids == expected_ids
    for q in TARGETED_VISUAL_QUESTIONS:
        assert q.bad_answer in ("yes", "no")
        assert q.penalty > 0.0
        assert len(q.defect_desc) > 0
        assert len(q.suggested_fix) > 0


def test_heuristic_critic_detects_empty_black_screen(black_frame: Path):
    """Verify that a black/empty canvas fails the scene_empty check with score 0.0."""
    critic = HeuristicVisionCritic()
    ctx = VisualContext(concept="Euler's Formula", latex_formula=r"e^{i\pi} + 1 = 0")
    verdict = critic.critique_frame(black_frame, ctx)

    assert verdict.passed is False
    assert verdict.score == 0.0
    empty_checks = [c for c in verdict.checks if c.question_id == "scene_empty"]
    assert len(empty_checks) == 1
    assert empty_checks[0].passed is False
    assert any("completely blank or pitch black" in issue for issue in verdict.detected_issues)
    assert len(verdict.feedback_for_code_repair) > 0


def test_heuristic_critic_passes_valid_content(valid_slide_frame: Path):
    """Verify that a frame containing educational visual elements passes."""
    critic = HeuristicVisionCritic()
    ctx = VisualContext(concept="BODMAS Rule", latex_formula="3 + 4 x 2 = 11")
    verdict = critic.critique_frame(valid_slide_frame, ctx)

    assert verdict.passed is True
    assert verdict.score >= 0.70
    empty_checks = [c for c in verdict.checks if c.question_id == "scene_empty"]
    assert empty_checks[0].passed is True


def test_moondream_interrogation_protocol(valid_slide_frame: Path):
    """Verify MoondreamCritic interrogates the 10 questions and compiles verdicts."""
    critic = MoondreamCritic(model_name="vikhyatk/moondream-0_5b")

    # Mock the internal query method to return deterministic answers
    def mock_ask(img_path, pil_img, question):
        q_lower = question.lower()
        if "empty" in q_lower or "blank" in q_lower:
            return "No"
        if "cut off" in q_lower or "clipped" in q_lower:
            return "Yes"  # Simulate a cutoff defect
        if "overlapping" in q_lower:
            return "No"
        return "Yes"

    with patch.object(critic, "_ask_question", side_effect=mock_ask):
        ctx = VisualContext(concept="Fourier Transform", latex_formula=r"\hat{f}(\xi)")
        verdict = critic.critique_frame(valid_slide_frame, ctx)

        assert len(verdict.checks) == 10
        # Cutoff was flagged as "Yes" (bad_answer is "yes") -> should fail
        cutoff_check = next(c for c in verdict.checks if c.question_id == "equation_cutoff")
        assert cutoff_check.passed is False
        assert any("cut off or clipping" in issue for issue in verdict.detected_issues)
        assert verdict.passed is False  # Because cutoff is critical


def test_openrouter_gemini_flash_parsing(valid_slide_frame: Path):
    """Verify OpenRouterVisionCritic parses structured JSON verdict for Gemini 2.5 Flash."""
    critic = OpenRouterVisionCritic(model_name="google/gemini-2.5-flash")

    mock_json_response = {
        "checks": [
            {"id": "scene_empty", "passed": True, "detail": "Valid elements"},
            {"id": "equation_visible", "passed": True, "detail": "MathTex visible"},
            {"id": "equation_cutoff", "passed": False, "detail": "Right edge clipped at x > 6.5"},
            {"id": "objects_overlapping", "passed": True, "detail": "Good vertical spacing"},
            {"id": "text_too_small", "passed": True, "detail": "Font size 32"},
            {"id": "excessive_empty_space", "passed": True, "detail": "Well-balanced"},
            {"id": "diagram_appeared", "passed": True, "detail": "Unit circle present"},
            {"id": "stuck_frame", "passed": True, "detail": "Settled"},
            {"id": "labels_readable", "passed": True, "detail": "High contrast"},
            {"id": "layout_coherent", "passed": True, "detail": "Coherent"},
        ],
        "detected_issues": ["Right edge clipped at x > 6.5"],
        "suggested_fixes": ["formula.scale_to_fit_width(11.0)"],
    }

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = f"```json\n{import_json(mock_json_response)}\n```"
    mock_resp.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_resp

    with patch.object(critic, "_get_client", return_value=mock_client):
        ctx = VisualContext(concept="Geometric Projections")
        verdict = critic.critique_frame(valid_slide_frame, ctx)

        assert verdict.critic_model == "google/gemini-2.5-flash"
        assert verdict.backend == "openrouter"
        assert verdict.passed is False  # Due to cutoff
        assert any("clipping" in issue or "clipped" in issue for issue in verdict.detected_issues)
        assert "scale_to_fit_width" in verdict.feedback_for_code_repair


def test_hybrid_critic_escalation(valid_slide_frame: Path):
    """Verify HybridVisionCritic passes front-line if score is high, or escalates to Gemini on defect."""
    hybrid = HybridVisionCritic(
        moondream_model="vikhyatk/moondream-0_5b",
        escalation_model="google/gemini-2.5-flash",
        escalation_threshold=0.85,
    )

    # Case A: Moondream passes cleanly -> No escalation
    clean_verdict = VisualCriticVerdict(
        passed=True,
        score=0.95,
        critic_model="vikhyatk/moondream-0_5b",
        backend="moondream",
        checks=[],
    )
    with patch.object(hybrid.primary_critic, "critique_frame", return_value=clean_verdict):
        with patch.object(hybrid.escalation_critic, "critique_frame") as mock_esc:
            res = hybrid.critique_frame(valid_slide_frame)
            assert res.passed is True
            assert res.backend == "hybrid:moondream"
            mock_esc.assert_not_called()

    # Case B: Moondream detects issue -> Escalates to Gemini Flash
    defect_verdict = VisualCriticVerdict(
        passed=False,
        score=0.60,
        critic_model="vikhyatk/moondream-0_5b",
        backend="moondream",
        detected_issues=["Overlapping text"],
        suggested_fixes=["Add buff=0.35"],
    )
    escalated_verdict = VisualCriticVerdict(
        passed=False,
        score=0.65,
        critic_model="google/gemini-2.5-flash",
        backend="openrouter",
        detected_issues=["Overlapping text", "Right formula cutoff"],
        suggested_fixes=["Add buff=0.35", "Scale to fit width"],
    )
    with patch.object(hybrid.primary_critic, "critique_frame", return_value=defect_verdict):
        with patch.object(hybrid.escalation_critic, "critique_frame", return_value=escalated_verdict):
            res = hybrid.critique_frame(valid_slide_frame)
            assert res.backend == "hybrid:escalated"
            assert "Right formula cutoff" in res.detected_issues


def test_visual_critic_factory_model_swapping():
    """Verify get_visual_critic dynamically swaps backends and models via parameters or env vars."""
    # 1. Moondream 0.5B
    c1 = get_visual_critic(backend="moondream", model="vikhyatk/moondream-0_5b")
    assert isinstance(c1, MoondreamCritic)
    assert c1.model_name == "vikhyatk/moondream-0_5b"

    # 2. Swap to higher Moondream model (e.g. 2B or fine-tuned)
    c2 = get_visual_critic(backend="moondream", model="vikhyatk/moondream2")
    assert isinstance(c2, MoondreamCritic)
    assert c2.model_name == "vikhyatk/moondream2"

    # 3. Swap to Google Gemini 2.5 Flash
    c3 = get_visual_critic(backend="openrouter", model="google/gemini-2.5-flash")
    assert isinstance(c3, OpenRouterVisionCritic)
    assert c3.model_name == "google/gemini-2.5-flash"

    # 4. Swap to Ollama
    c4 = get_visual_critic(backend="ollama", model="qwen2.5-vl:7b")
    assert isinstance(c4, OllamaVisionCritic)
    assert c4.model_name == "qwen2.5-vl:7b"

    # 5. Hybrid
    c5 = get_visual_critic(backend="hybrid", model="google/gemini-2.5-flash")
    assert isinstance(c5, HybridVisionCritic)

    # 6. Heuristic
    c6 = get_visual_critic(backend="heuristic")
    assert isinstance(c6, HeuristicVisionCritic)


def test_code_repair_feedback_formatting():
    """Verify the generated code repair prompt contains actionable spatial guidance."""
    critic = HeuristicVisionCritic()
    ctx = VisualContext(
        concept="Euler's Formula",
        latex_formula=r"e^{i\theta} = \cos\theta + i\sin\theta",
    )
    issues = ["Equation extends off screen edge", "Text overlapping with axes"]
    fixes = ["formula.scale_to_fit_width(11.0)", ".next_to(axes, DOWN, buff=0.4)"]

    feedback = critic.build_repair_feedback(issues, fixes, ctx)

    assert "VISUAL CRITIC FEEDBACK" in feedback
    assert "Equation extends off screen edge" in feedback
    assert "Text overlapping with axes" in feedback
    assert "formula.scale_to_fit_width(11.0)" in feedback
    assert r"e^{i\theta} = \cos\theta + i\sin\theta" in feedback


def test_repair_visual_anchor_code():
    """Verify repair_visual_anchor_code formats critic feedback and parses repaired code."""
    from ir import TeachingSegment, VisualAnchor
    from keyframe_engine import repair_visual_anchor_code

    segment = TeachingSegment(
        slide_num=1,
        concept="BODMAS Rule",
        visual_anchor=VisualAnchor(
            latex="3 + 4 x 2 = 11",
            visible_elements=["3", "4", "2", "11"],
            key_definitions=["Multiplication before addition"],
        ),
        manim_code="title = Text('BODMAS')\nself.play(Write(title))",
    )

    verdict = VisualCriticVerdict(
        passed=False,
        score=0.4,
        critic_model="moondream-0.5b",
        backend="moondream",
        detected_issues=["Formula clipped at right margin"],
        suggested_fixes=["formula.scale_to_fit_width(11.0)"],
        feedback_for_code_repair="Formula clipped at right margin. Use formula.scale_to_fit_width(11.0).",
    )

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "```python\ntitle = Text('BODMAS')\nformula = MathTex('3 + 4 x 2 = 11').scale_to_fit_width(11.0)\nself.play(Write(title), Write(formula))\n```"
    mock_resp.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_resp

    repaired = repair_visual_anchor_code(
        original_code=segment.manim_code,
        segment=segment,
        verdict=verdict,
        client=mock_client,
        model="gpt-4o-mini",
    )

    assert "scale_to_fit_width(11.0)" in repaired
    assert mock_client.chat.completions.create.called


def import_json(data):
    import json
    return json.dumps(data)


"""Hybrid Visual Critic: Moondream 0.5B first-pass with Frontier Escalation (Gemini Flash)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from .base import BaseVisualCritic
from .moondream import MoondreamCritic
from .openrouter import OpenRouterVisionCritic
from .types import VisualContext, VisualCriticVerdict


class HybridVisionCritic(BaseVisualCritic):
    """Tiered Hybrid Critic implementing the multi-layer evaluation strategy:

    1. Moondream 0.5B acts as the fast, local front-line filter inspecting the
       10 targeted visual constraints (empty frame, clipping, overlap, small text).
    2. If Moondream passes cleanly (score >= 0.85 and 0 defects), the frame is accepted.
    3. If Moondream detects an issue or if the score is borderline (< 0.85),
       the frame is escalated to OpenRouter (Google Gemini 2.5 Flash / GPT-4o)
       to perform deep multimodal reasoning and produce high-precision code fixes.
    """

    def __init__(
        self,
        moondream_model: str = "vikhyatk/moondream-0_5b",
        escalation_model: str = "google/gemini-2.5-flash",
        pass_threshold: float = 0.70,
        escalation_threshold: float = 0.85,
    ) -> None:
        super().__init__(
            model_name=f"{moondream_model}+{escalation_model}",
            backend_name="hybrid",
            pass_threshold=pass_threshold,
        )
        self.primary_critic = MoondreamCritic(model_name=moondream_model, pass_threshold=pass_threshold)
        self.escalation_critic = OpenRouterVisionCritic(model_name=escalation_model, pass_threshold=pass_threshold)
        self.escalation_threshold = escalation_threshold

    def critique_frame(
        self,
        image_path: Path | str,
        context: Optional[VisualContext] = None,
    ) -> VisualCriticVerdict:
        img_p = Path(image_path).resolve()

        # Step 1: Front-line pass with Moondream 0.5B
        print(f"[HybridVisionCritic] Step 1: Interrogating keyframe with {self.primary_critic.model_name}...", file=sys.stderr)
        primary_verdict = self.primary_critic.critique_frame(img_p, context)

        # If primary clearly passed with high confidence, accept immediately
        if primary_verdict.passed and primary_verdict.score >= self.escalation_threshold:
            print(f"[HybridVisionCritic] Passed clean on Moondream (score: {primary_verdict.score:.2f}). No escalation needed.", file=sys.stderr)
            primary_verdict.backend = "hybrid:moondream"
            return primary_verdict

        # Step 2: Escalate to Google Gemini Flash for deep spatial reasoning & repair guidance
        reason = "defects detected" if not primary_verdict.passed else f"score {primary_verdict.score:.2f} < {self.escalation_threshold}"
        print(f"[HybridVisionCritic] Step 2: Escalating to {self.escalation_critic.model_name} ({reason})...", file=sys.stderr)

        escalated_verdict = self.escalation_critic.critique_frame(img_p, context)
        escalated_verdict.backend = "hybrid:escalated"

        # Combine detected issues from both models for richer feedback
        combined_issues = list(dict.fromkeys(primary_verdict.detected_issues + escalated_verdict.detected_issues))
        combined_fixes = list(dict.fromkeys(escalated_verdict.suggested_fixes + primary_verdict.suggested_fixes))

        escalated_verdict.detected_issues = combined_issues
        escalated_verdict.suggested_fixes = combined_fixes
        escalated_verdict.feedback_for_code_repair = self.build_repair_feedback(
            combined_issues, combined_fixes, context
        )

        return escalated_verdict

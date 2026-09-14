"""Ollama multimodal vision critic implementation."""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .base import BaseVisualCritic
from .heuristic import HeuristicVisionCritic
from .types import (
    TARGETED_VISUAL_QUESTIONS,
    VisualCheckItem,
    VisualContext,
    VisualCriticVerdict,
)


class OllamaVisionCritic(BaseVisualCritic):
    """Visual Critic using Ollama vision models (e.g. moondream, qwen2.5-vl)."""

    def __init__(
        self,
        model_name: str = "moondream",
        base_url: Optional[str] = None,
        pass_threshold: float = 0.70,
    ) -> None:
        super().__init__(model_name=model_name, backend_name="ollama", pass_threshold=pass_threshold)
        raw_base = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.base_url = raw_base.rstrip("/").removesuffix("/v1")
        self._fallback = HeuristicVisionCritic()

    def critique_frame(
        self,
        image_path: Path | str,
        context: Optional[VisualContext] = None,
    ) -> VisualCriticVerdict:
        img_p = Path(image_path).resolve()
        if not img_p.is_file():
            return self._fallback.critique_frame(image_path, context)

        # Pre-flight heuristic check
        h_verdict = self._fallback.critique_frame(img_p, context)
        if not h_verdict.passed:
            for chk in h_verdict.checks:
                if chk.question_id == "scene_empty" and not chk.passed:
                    return self.compile_verdict(
                        checks=h_verdict.checks,
                        keyframe_path=str(img_p),
                        context=context,
                        raw_response={"reason": "Pre-flight heuristic caught empty/black canvas"},
                    )

        try:
            with open(img_p, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")

            checks: List[VisualCheckItem] = []
            raw_answers: Dict[str, str] = {}

            # Targeted interrogation loop over Ollama API
            url = f"{self.base_url}/api/generate"
            clean_model = self.model_name.removeprefix("ollama:").strip()

            for q_def in TARGETED_VISUAL_QUESTIONS:
                prompt = f"{q_def.question} Answer strictly with 'Yes' or 'No'."
                payload = {
                    "model": clean_model,
                    "prompt": prompt,
                    "images": [b64_img],
                    "stream": False,
                    "options": {"temperature": 0.0},
                }

                try:
                    resp = httpx.post(url, json=payload, timeout=25.0)
                    resp.raise_for_status()
                    ans = resp.json().get("response", "").strip()
                except Exception as call_err:
                    print(f"[OllamaVisionCritic] Check '{q_def.id}' error: {call_err}", file=sys.stderr)
                    ans = "unknown"

                raw_answers[q_def.id] = ans
                ans_lower = ans.lower()

                is_bad = False
                if q_def.bad_answer == "yes":
                    is_bad = "yes" in ans_lower and "no" not in ans_lower
                elif q_def.bad_answer == "no":
                    is_bad = "no" in ans_lower and "yes" not in ans_lower

                checks.append(
                    VisualCheckItem(
                        question_id=q_def.id,
                        question_text=q_def.question,
                        passed=not is_bad,
                        raw_answer=ans,
                        detail=f"Answer: {ans}",
                    )
                )

            return self.compile_verdict(
                checks=checks,
                keyframe_path=str(img_p),
                context=context,
                raw_response=raw_answers,
            )

        except Exception as exc:
            print(f"[OllamaVisionCritic] Execution failed: {exc}. Falling back to heuristic.", file=sys.stderr)
            verdict = self._fallback.critique_frame(img_p, context)
            verdict.critic_model = f"{self.model_name} (fallback:{verdict.critic_model})"
            return verdict

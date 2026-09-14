"""OpenRouter / Google Gemini Flash Vision Critic implementation."""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .base import BaseVisualCritic
from .heuristic import HeuristicVisionCritic
from .types import (
    TARGETED_VISUAL_QUESTIONS,
    VisualCheckItem,
    VisualContext,
    VisualCriticVerdict,
)


OPENROUTER_CRITIC_PROMPT = """You are an authoritative visual quality critic inspecting a rendered Manim animation keyframe.
You must evaluate the keyframe across the following 10 targeted visual questions:

1. scene_empty: Is this image completely blank, pitch black, or empty with no visual content?
2. equation_visible: Is a mathematical formula, equation, or primary text clearly visible?
3. equation_cutoff: Is any equation, formula, or text cut off, clipped, or running off the screen edges?
4. objects_overlapping: Are any text elements, formulas, or shapes overlapping or colliding?
5. text_too_small: Is any text or formula excessively tiny or difficult to read?
6. excessive_empty_space: Is there excessive empty space making the slide bare?
7. diagram_appeared: If coordinate axes, geometric shapes, or plots were intended, are they clearly present?
8. stuck_frame: Is the visual animation stuck on an unintended intermediate transition or broken frame?
9. labels_readable: Are all text labels and annotations clearly readable with strong contrast?
10. layout_coherent: Is the overall visual layout organized, coherent, and educationally well-balanced?

Output your verdict STRICTLY as a JSON object with this exact structure:
```json
{
  "checks": [
    {"id": "scene_empty", "passed": true, "detail": "Canvas has elements"},
    {"id": "equation_visible", "passed": true, "detail": "Formula clearly visible"},
    {"id": "equation_cutoff", "passed": true, "detail": "Within frame boundaries"},
    {"id": "objects_overlapping", "passed": true, "detail": "No collisions detected"},
    {"id": "text_too_small", "passed": true, "detail": "Readable size"},
    {"id": "excessive_empty_space", "passed": true, "detail": "Well-balanced"},
    {"id": "diagram_appeared", "passed": true, "detail": "Diagram present"},
    {"id": "stuck_frame", "passed": true, "detail": "Settled frame"},
    {"id": "labels_readable", "passed": true, "detail": "High contrast"},
    {"id": "layout_coherent", "passed": true, "detail": "Clean hierarchy"}
  ],
  "detected_issues": ["Issue description if any"],
  "suggested_fixes": ["Concrete Manim code fix if needed"]
}
```
"""


class OpenRouterVisionCritic(BaseVisualCritic):
    """Visual Critic using frontier VLMs like Google Gemini 2.5 Flash / GPT-4o via OpenRouter."""

    def __init__(
        self,
        model_name: str = "google/gemini-2.5-flash",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        pass_threshold: float = 0.70,
    ) -> None:
        super().__init__(model_name=model_name, backend_name="openrouter", pass_threshold=pass_threshold)
        self.api_key = (
            api_key
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("AOS_OPENROUTER_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "local"
        ).strip()
        self.base_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        ).strip()
        self._client: Optional[OpenAI] = None
        self._fallback = HeuristicVisionCritic()

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=12.0,
                max_retries=1,
            )
        return self._client

    def critique_frame(
        self,
        image_path: Path | str,
        context: Optional[VisualContext] = None,
    ) -> VisualCriticVerdict:
        img_p = Path(image_path).resolve()
        if not img_p.is_file():
            return self._fallback.critique_frame(image_path, context)

        # Quick heuristic pre-flight check for blank screen
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
                b64_image = base64.b64encode(f.read()).decode("utf-8")

            ctx_info = ""
            if context:
                ctx_info = (
                    f"\nContext:\n- Concept: {context.concept}\n"
                    f"- Expected Formula: {context.latex_formula}\n"
                    f"- Intended Elements: {context.visible_elements}\n"
                )

            client = self._get_client()
            clean_model = self.model_name.removeprefix("openrouter:").strip()

            messages = [
                {"role": "system", "content": OPENROUTER_CRITIC_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Evaluate this Manim slide keyframe.{ctx_info}"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                        },
                    ],
                },
            ]

            resp = client.chat.completions.create(
                model=clean_model,
                messages=messages,
                temperature=0.0,
            )

            raw_text = resp.choices[0].message.content or "{}"
            json_match = re.search(r"```(?:json)?(.*?)```", raw_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1).strip())
            else:
                data = json.loads(raw_text.strip())

            checks: List[VisualCheckItem] = []
            parsed_checks = data.get("checks", [])
            chk_dict = {c.get("id"): c for c in parsed_checks if isinstance(c, dict)}

            for q_def in TARGETED_VISUAL_QUESTIONS:
                item = chk_dict.get(q_def.id)
                if item:
                    passed = bool(item.get("passed", True))
                    detail = str(item.get("detail", ""))
                else:
                    passed = True
                    detail = "Not explicitly flagged"

                checks.append(
                    VisualCheckItem(
                        question_id=q_def.id,
                        question_text=q_def.question,
                        passed=passed,
                        detail=detail,
                    )
                )

            return self.compile_verdict(
                checks=checks,
                keyframe_path=str(img_p),
                context=context,
                raw_response=data,
            )

        except Exception as exc:
            print(f"[OpenRouterVisionCritic] API critique error: {exc}. Falling back to heuristic.", file=sys.stderr)
            verdict = self._fallback.critique_frame(img_p, context)
            verdict.critic_model = f"{self.model_name} (fallback:{verdict.critic_model})"
            return verdict
